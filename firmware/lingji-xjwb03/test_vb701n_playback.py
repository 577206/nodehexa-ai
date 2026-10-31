"""Exercise the real driver's pacing/drain C code with a deterministic UART clock."""
import shutil
import subprocess
from pathlib import Path
import pytest


def test_pcm_fifo_pacing_and_tail_drain(tmp_path):
    compiler = shutil.which('cc')
    if not compiler:
        pytest.skip('C compiler needed for driver timing test')
    source = (Path(__file__).parent / 'sdk/qumios-dev/platform/mcu/esp32s3/qm_audio/qm_audio_device_vb701n.c').read_text()
    pacing = source[source.index('static int wait_gap('):source.index('static void send_pcm_lead_silence(')]
    drain = source[source.index('int qm_audio_device_playback_drain('):source.index('int qm_audio_device_playback_pause(')]
    stub = r'''
#include <stdint.h>
#include <stddef.h>
#include <assert.h>
#define QM_EOK 0
#define QM_ETIMEOUT 2
#define QM_EIO 8
#define QM_EINTR 9
#define QM_EINVAL 10
#define QM_EINIT 11
#define QM_WAIT_FOREVER UINT32_MAX
#define CONFIG_QM_VB701N_TX_INTERVAL_MS 5
#define VB701N_TX_BURST_FRAMES 2
#define VB701N_CMD_HOST_SPK_AUDIO 1
static uint32_t clock_ms=100, g_last_send_ms, g_last_send_duration_ms;
static int g_abort_write, g_open=1, g_mute, busy;
static uint32_t g_play_frame_len=320, g_play_frame_ms=10;
static unsigned sends;
typedef struct {uint32_t at;} qm_utils_time_t;
static uint32_t qm_now_ms(void) {return clock_ms;}
static void qm_msleep(uint32_t ms) {clock_ms+=ms;}
static void qm_utils_time_countdown_ms(qm_utils_time_t *t,uint32_t ms) {t->at=clock_ms+ms;}
static int qm_utils_time_is_expired(qm_utils_time_t *t) {return (int32_t)(clock_ms-t->at)>=0;}
static int flow_is_busy(void) {return busy;}
static int vb701n_proto_send(int command,const uint8_t *data,uint16_t n) {sends++;return 0;}
'''
    checks = r'''
int main(void) {
 uint8_t pcm[640]={0};
 /* 200 ms lead silence, then 2 seconds of audio: same FIFO clock. */
 for(int i=0;i<20;i++) assert(pace_send(pcm,320,1000)==0);
 assert(clock_ms==290);
 for(int i=0;i<100;i++) assert(pace_send(pcm,640,1000)==0);
 assert(clock_ms==2280 && sends==220);
 assert(qm_audio_device_playback_drain(0,10)==-QM_ETIMEOUT);
 assert(qm_audio_device_playback_drain(0,100)==0 && clock_ms==2300);
 /* Backpressure must have a finite timeout and not send partial extra PCM. */
 busy=1;
 assert(pace_send(pcm,640,100)==-QM_ETIMEOUT && sends==220);
 busy=0;
 assert(pace_send(pcm,640,100)==0);
 g_abort_write=1;
 assert(qm_audio_device_playback_drain(0,100)==-QM_EINTR);
 return 0;
}
'''
    c = tmp_path / 'pacing.c'
    c.write_text(stub + pacing + drain + checks)
    binary = tmp_path / 'pacing'
    subprocess.run([compiler, '-std=c11', str(c), '-o', str(binary)], check=True, capture_output=True)
    subprocess.run([str(binary)], check=True, capture_output=True, timeout=3)
    assert 'QM_AUDIO_DEVICE_CAP_DRAIN |' in source
