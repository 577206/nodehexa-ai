#include "direct_audio.h"
#include "voice.h"
#include "qm_audio.h"
#include "qm_log.h"
#include "esp_random.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include <stdatomic.h>
#include <string.h>

#define MAX_PACKET 255U
#define UP_SLOTS 32U
#define DOWN_SLOTS 64U
#define LOG_TAG "direct_audio"
typedef struct { uint32_t generation; uint16_t length; uint8_t kind; uint8_t data[MAX_PACKET]; } record_t;
static QueueHandle_t up_queue, down_queue;
static SemaphoreHandle_t admission;
static qm_audio_capture_subscription_t *capture;
static qm_audio_control_t *control;
static atomic_uint generation, state, peer_tick;
static atomic_bool wake_pending;
static qm_audio_operation_id_t operation;
static TickType_t deadline, drain_deadline, resume_at;
static bool draining, capturing;
static unsigned play_packets;
static TickType_t play_started;

static uint32_t get32(const uint8_t *p) { return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24; }
static void put32(uint8_t *p,uint32_t v) { for(unsigned i=0;i<4;i++) p[i]=(uint8_t)(v>>(8*i)); }
static bool elapsed(TickType_t now,TickType_t target) { return (int32_t)(now-target)>=0; }
static void on_wake(void) { atomic_store(&wake_pending,true); }
static void gate(bool enable)
{
    if(capturing!=enable) {
        int rc=qm_audio_capture_enable(capture,enable ? QM_TRUE : QM_FALSE);
        if(rc==QM_EOK) capturing=enable;
        else QM_LOGW(LOG_TAG,"capture gate failed %d",rc);
    }
}
static void stop_output(void)
{
    if(operation) {
        (void)qm_audio_control_stop(control,operation,1);
        (void)qm_audio_control_release(control,operation,1000);
        operation=0;
    }
    draining=false;
}
static void idle(void)
{
    atomic_store(&state,0);
    gate(false);
    stop_output();
    xSemaphoreTake(admission,portMAX_DELAY);
    xQueueReset(up_queue); xQueueReset(down_queue);
    xSemaphoreGive(admission);
    resume_at=0;
}
static int start_output(void)
{
    stop_output(); gate(false);
    play_packets=0; play_started=xTaskGetTickCount();
    qm_audio_control_play_request_t request={0};
    request.source.type=QM_AUDIO_SOURCE_PUSH;
    request.source.value.push.buffer_bytes=4096;
    request.codec.codec=QM_AUDIO_CODEC_OPUS;
    request.codec.framing=QM_AUDIO_CODEC_FRAMING_PACKET;
    request.codec.packet_duration_ms=20;
    request.codec.pcm.sample_rate_hz=16000;
    request.codec.pcm.channels=1;
    request.codec.pcm.sample=QM_AUDIO_PCM_S16;
    request.priority=QM_AUDIO_PRIORITY_NORMAL;
    request.admission=QM_AUDIO_ADMISSION_PREEMPT_LOWER;
    request.admission_timeout_ms=800;
    return qm_audio_control_play(control,&request,&operation);
}
static void worker(void *arg)
{
    (void)arg;
    record_t packet;
    uint8_t native[512];
    for(;;) {
        TickType_t now=xTaskGetTickCount();
        if(atomic_exchange(&wake_pending,false)) {
            idle();
            atomic_fetch_add(&generation,1);
            atomic_store(&peer_tick,now);
            atomic_store(&state,1);
            deadline=now+pdMS_TO_TICKS(30000);
            gate(true);
            QM_LOGI(LOG_TAG,"local wake generation=%u",atomic_load(&generation));
        }
        if(atomic_load(&state) &&
           (elapsed(now,deadline) || elapsed(now,atomic_load(&peer_tick)+pdMS_TO_TICKS(6000)))) idle();
        if(resume_at && elapsed(now,resume_at) && atomic_load(&state)) {
            resume_at=0; atomic_store(&state,1);
            deadline=now+pdMS_TO_TICKS(30000); gate(true);
        }
        if(xQueueReceive(down_queue,&packet,0)==pdTRUE && packet.generation==atomic_load(&generation) && atomic_load(&state)) {
            deadline=now+pdMS_TO_TICKS(60000);
            switch(packet.kind) {
            case 1:
                resume_at=0;
                if(start_output()!=QM_EOK) { QM_LOGW(LOG_TAG,"play admission failed"); idle(); }
                else atomic_store(&state,3);
                break;
            case 2:
                if(operation && !draining) {
                    qm_audio_data_t data={.data=packet.data,.size=packet.length,.duration_ms=20,.flags=QM_AUDIO_DATA_DURATION_VALID};
                    int rc=qm_audio_control_stream_write_packet(control,operation,&data,1000);
                    if(rc!=QM_EOK) { QM_LOGW(LOG_TAG,"play write failed %d after %u packets",rc,play_packets); idle(); }
                    else play_packets++;
                }
                break;
            case 3:
                if(operation) {
                    if(qm_audio_control_stream_finish(control,operation)!=QM_EOK) idle();
                    else { draining=true; drain_deadline=now+pdMS_TO_TICKS(10000); }
                } else { resume_at=now+pdMS_TO_TICKS(400); }
                break;
            case 4: gate(false); xQueueReset(up_queue); atomic_store(&state,2); break;
            case 5: idle(); break;
            case 6: break;
            }
        }
        if(draining && operation) {
            int rc=qm_audio_control_wait(control,operation,0);
            if(rc!= -QM_ETIMEOUT || elapsed(now,drain_deadline)) {
                QM_LOGI(LOG_TAG,"play complete result=%d packets=%u audio_ms=%u elapsed_ms=%u",
                    rc,play_packets,play_packets*20,(unsigned)((xTaskGetTickCount()-play_started)*portTICK_PERIOD_MS));
                stop_output();
                atomic_store(&state,2);
                resume_at=now+pdMS_TO_TICKS(500);
            }
        }
        if(capturing && atomic_load(&state)==1) {
            qm_audio_data_t data={.data=native,.size=sizeof(native)};
            if(qm_audio_capture_recv(capture,&data,0)==QM_EOK && data.size>0 && data.size<=MAX_PACKET) {
                packet.generation=atomic_load(&generation); packet.kind=2; packet.length=data.size;
                memcpy(packet.data,native,data.size);
                if(xQueueSend(up_queue,&packet,0)!=pdTRUE) {
                    record_t dropped;
                    (void)xQueueReceive(up_queue,&dropped,0);
                    (void)xQueueSend(up_queue,&packet,0);
                }
            }
        }
        vTaskDelay(pdMS_TO_TICKS(2));
    }
}
int direct_audio_init(void)
{
    up_queue=xQueueCreate(UP_SLOTS,sizeof(record_t));
    down_queue=xQueueCreate(DOWN_SLOTS,sizeof(record_t));
    admission=xSemaphoreCreateMutex();
    qm_audio_capture_config_t config={.queue_len=UP_SLOTS,.enabled=QM_FALSE,.delivery=QM_AUDIO_CAPTURE_DELIVERY_QUEUE};
    if(!up_queue || !down_queue || !admission ||
       qm_audio_capture_subscribe(qm_audio_get_capture(),&config,&capture)!=QM_EOK ||
       qm_audio_control_create(&control)!=QM_EOK) return -1;
    atomic_store(&generation,esp_random());
    if(xTaskCreate(worker,"direct_audio",8192,NULL,6,NULL)!=pdPASS) return -1;
    voice_set_wakeup_cb(on_wake);
    QM_LOGI(LOG_TAG,"Qwen direct audio ready; cloud mic closed until local wake");
    return 0;
}
unsigned direct_audio_state(void) { return atomic_load(&state); }
uint32_t direct_audio_generation(void) { return atomic_load(&generation); }
size_t direct_audio_read(uint8_t *out,size_t capacity)
{
    if(!up_queue || capacity<12) return 0;
    atomic_store(&peer_tick,xTaskGetTickCount());
    memcpy(out,"LXA1",4); put32(out+4,atomic_load(&generation));
    out[8]=atomic_load(&state); out[9]=0; out[10]=out[11]=0;
    size_t used=12; unsigned count=0; record_t packet;
    while(count<12 && capacity-used>=MAX_PACKET+2 && xQueueReceive(up_queue,&packet,0)==pdTRUE) {
        if(packet.generation!=get32(out+4) || out[8]!=1) continue;
        out[used++]=packet.length & 255; out[used++]=packet.length>>8;
        memcpy(out+used,packet.data,packet.length); used+=packet.length; count++;
    }
    out[10]=count;
    return used;
}
int direct_audio_write(const uint8_t *data,size_t length)
{
    if(!down_queue || !admission) return 4;
    if(length<5 || data[4]<1 || data[4]>6) return 3;
    unsigned count=0; size_t offset=5;
    if(data[4]!=2 && length!=5) return 3;
    while(offset<length) {
        if(length-offset<2) return 3;
        unsigned n=data[offset] | (unsigned)data[offset+1]<<8; offset+=2;
        if(!n || n>MAX_PACKET || n>length-offset) return 3;
        offset+=n; count++;
    }
    if(data[4]==2 && !count) return 3;
    xSemaphoreTake(admission,portMAX_DELAY);
    int result=0;
    if(get32(data)!=atomic_load(&generation) || !atomic_load(&state)) result=1;
    else if(uxQueueSpacesAvailable(down_queue)<(count?count:1)) result=2;
    else {
        record_t packet={.generation=get32(data),.kind=data[4]};
        offset=5;
        do {
            if(count) { packet.length=data[offset] | (unsigned)data[offset+1]<<8; offset+=2; memcpy(packet.data,data+offset,packet.length); offset+=packet.length; }
            (void)xQueueSend(down_queue,&packet,0);
        } while(offset<length);
        atomic_store(&peer_tick,xTaskGetTickCount());
    }
    xSemaphoreGive(admission);
    return result;
}
