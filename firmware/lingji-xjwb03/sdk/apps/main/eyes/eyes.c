#include "eyes.h"
#include "qm_config.h"
#include <stdatomic.h>
#include "esp_timer.h"
#include "esp_log.h"
#include "driver/i2c_master.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "../agent/direct_audio.h"
/* Confirmed by the user: left SDA P10/SCL P11, right SDA P6/SCL P7.
 * Camera owns I2C0. Left uses I2C1; right uses open-drain software I2C.
 * SH1106/128x64 remains a trial profile until the visible image is confirmed. */
#ifndef CONFIG_NODEHEXA_EYES
#define CONFIG_NODEHEXA_EYES 1
#endif
#ifndef EYES_SH1106
#define EYES_SH1106 0
#endif
#define EYES_SDA 10
#define EYES_SCL 11
#define RIGHT_SDA 6
#define RIGHT_SCL 7
#include "driver/gpio.h"
#include "esp_rom_sys.h"
typedef struct { i2c_master_dev_handle_t hw; uint8_t address; bool software; } display_t;
static void pause_bus(void){esp_rom_delay_us(2);}
static void sda(int level){gpio_set_level(RIGHT_SDA,level);pause_bus();}
static void scl_low(void){gpio_set_level(RIGHT_SCL,0);pause_bus();}
static bool scl_high(void){
 gpio_set_level(RIGHT_SCL,1);
 int64_t deadline=esp_timer_get_time()+1000;
 while(!gpio_get_level(RIGHT_SCL))if(esp_timer_get_time()>deadline)return false;
 pause_bus();return true;
}
static bool soft_stop(void){scl_low();sda(0);bool ok=scl_high();sda(1);return ok;}
static esp_err_t soft_byte(uint8_t value){
 for(int bit=7;bit>=0;bit--){scl_low();sda((value>>bit)&1);if(!scl_high())return ESP_ERR_TIMEOUT;}
 scl_low();sda(1);if(!scl_high())return ESP_ERR_TIMEOUT;
 bool ack=!gpio_get_level(RIGHT_SDA);scl_low();return ack?ESP_OK:ESP_ERR_NOT_FOUND;
}
static esp_err_t soft_send(uint8_t address,const uint8_t *p,size_t n){
 sda(1);if(!scl_high())return ESP_ERR_TIMEOUT;
 if(!gpio_get_level(RIGHT_SDA))return ESP_ERR_INVALID_STATE;
 sda(0);scl_low();esp_err_t err=soft_byte(address<<1);
 for(size_t i=0;i<n && err==ESP_OK;i++)err=soft_byte(p[i]);
 if(!soft_stop() && err==ESP_OK)err=ESP_ERR_TIMEOUT;
 return err;
}
static atomic_uint request;
static atomic_uint contrast_value=127, ready_mask, current_mode;
unsigned eyes_ready_mask(void){return atomic_load(&ready_mask);}
unsigned eyes_current_mode(void){return atomic_load(&current_mode);}
unsigned eyes_contrast(void){return atomic_load(&contrast_value);}
void eyes_control(int mode,unsigned ms,unsigned contrast){
 if(mode < -1 || mode>=EYE_MODE_COUNT || ms>10000 || contrast>255)return;
 atomic_store(&contrast_value,contrast);
 atomic_store(&request,mode<0?0x80000000u:((unsigned)mode<<16)|ms);
}
static TaskHandle_t task;
void eyes_expression(eye_mode_t m,unsigned ms){
 if(m>=EYE_MODE_COUNT)return;
 if(ms>10000)ms=10000;
 atomic_store(&request,((unsigned)m<<16)|ms);
}
static esp_err_t send(display_t *d,const uint8_t *p,size_t n){
 return d->software?soft_send(d->address,p,n):i2c_master_transmit(d->hw,p,n,50);
}
static esp_err_t init_display(display_t *d){
 const uint8_t common[]={0,0xae,0xd5,0x80,0xa8,0x3f,0xd3,0,0x40,0xa1,0xc8,0xda,0x12,0x81,0x7f,0xd9,0x22,0xdb,0x20,0xa4,0xa6};
 esp_err_t e=send(d,common,sizeof(common));if(e)return e;
 if(!EYES_SH1106){const uint8_t page_mode[]={0,0x20,0x02};e=send(d,page_mode,sizeof(page_mode));if(e)return e;}
 const uint8_t power[]={0,EYES_SH1106?0xad:0x8d,EYES_SH1106?0x8b:0x14,0xaf};
 return send(d,power,sizeof(power));
}
static esp_err_t draw(display_t *d,uint8_t *f){
 for(int page=0;page<8;page++){
  uint8_t pos[]={0,(uint8_t)(0xb0+page),EYES_SH1106?2:0,0x10};
  esp_err_t e=send(d,pos,sizeof(pos));if(e)return e;
  uint8_t row[129];row[0]=0x40;
  for(int x=0;x<128;x++)row[x+1]=f[page*128+x];
  e=send(d,row,sizeof(row));if(e)return e;
 }return ESP_OK;
}
static void run(void *unused){
 (void)unused;
 i2c_master_bus_handle_t bus=NULL;
 i2c_master_bus_config_t c={.i2c_port=1,.sda_io_num=EYES_SDA,.scl_io_num=EYES_SCL,.clk_source=I2C_CLK_SRC_DEFAULT,.glitch_ignore_cnt=7,.flags.enable_internal_pullup=true};
 if(i2c_new_master_bus(&c,&bus)!=ESP_OK){ESP_LOGE("eyes","I2C1 unavailable");task=NULL;vTaskDelete(NULL);return;}
 gpio_set_level(RIGHT_SDA,1);gpio_set_level(RIGHT_SCL,1);
 gpio_config_t pins={.pin_bit_mask=(1ULL<<RIGHT_SDA)|(1ULL<<RIGHT_SCL),.mode=GPIO_MODE_INPUT_OUTPUT_OD,.pull_up_en=GPIO_PULLUP_ENABLE};
 if(gpio_config(&pins)!=ESP_OK){ESP_LOGE("eyes","right GPIO init failed");i2c_del_master_bus(bus);task=NULL;vTaskDelete(NULL);return;}
 unsigned applied_contrast[2]={256,256};
 display_t dev[2]={{0},{.software=true}};bool ready[2]={0};uint32_t retry[2]={0};
 ESP_LOGI("eyes","enabled: left SDA=10 SCL=11 I2C1; right SDA=6 SCL=7 software; trial SH1106=%d",EYES_SH1106);
 uint8_t frame[EYE_BYTES];uint32_t start=esp_timer_get_time()/1000,until=0,changed=0;
 eye_mode_t mode=EYE_IDLE,override=EYE_IDLE;
 for(;;){
  uint32_t now=(uint32_t)(esp_timer_get_time()/1000)-start;
  unsigned r=atomic_exchange(&request,0);
  if(r==0x80000000u){until=now;r=0;}
  if(r){override=(eye_mode_t)(r>>16);until=now+(r&65535);changed=now;}
  eye_mode_t next=EYE_IDLE;
#if CONFIG_NODEHEXA_QWEN_DIRECT
  unsigned state=direct_audio_state();
  next=state==1?EYE_LISTEN:state==2?EYE_THINK:state==3?EYE_SPEAK:EYE_IDLE;
#endif
  if((int32_t)(until-now)>0)next=override;
  if(mode!=next){mode=next;changed=now;ESP_LOGI("eyes","animation mode=%u",(unsigned)mode);}
  atomic_store(&current_mode,(unsigned)mode);
  for(int i=0;i<2;i++){
   if(!ready[i] && (int32_t)(now-retry[i])>=0){
    if(dev[i].hw){i2c_master_bus_rm_device(dev[i].hw);dev[i].hw=NULL;}
    dev[i].address=0;
    for(uint8_t address=0x3c;address<=0x3d;address++){
     esp_err_t probe=i?soft_send(address,NULL,0):i2c_master_probe(bus,address,30);
     if(probe==ESP_OK){dev[i].address=address;break;}
    }
    if(dev[i].address){
     esp_err_t err=ESP_OK;
     if(!i){
      i2c_device_config_t d={.dev_addr_length=I2C_ADDR_BIT_LEN_7,.device_address=dev[i].address,.scl_speed_hz=100000};
      err=i2c_master_bus_add_device(bus,&d,&dev[i].hw);
     }
     if(err==ESP_OK)err=init_display(&dev[i]);
     ready[i]=err==ESP_OK;applied_contrast[i]=256;
     ESP_LOGI("eyes","%s ACK address=0x%02x init=%s",i?"right":"left",dev[i].address,esp_err_to_name(err));
    }else ESP_LOGW("eyes","%s no ACK at 0x3c/0x3d",i?"right":"left");
    retry[i]=now+5000;
   }
   if(ready[i]){
    unsigned contrast=atomic_load(&contrast_value);
    if(applied_contrast[i]!=contrast){
     uint8_t cmd[]={0,0x81,(uint8_t)contrast};
     if(send(&dev[i],cmd,sizeof(cmd))==ESP_OK)applied_contrast[i]=contrast;
    }
    eye_render(frame,i,mode,now,now-changed);
    esp_err_t err=draw(&dev[i],frame);
    if(err!=ESP_OK){ESP_LOGW("eyes","%s frame failed: %s",i?"right":"left",esp_err_to_name(err));ready[i]=false;retry[i]=now+5000;}
   }
  }
  atomic_store(&ready_mask,(ready[0]?1u:0u)|(ready[1]?2u:0u));
  vTaskDelay(pdMS_TO_TICKS(50));
 }
}
void eyes_start(void){
 if(CONFIG_NODEHEXA_EYES && !task && xTaskCreate(run,"eyes",4096,NULL,2,&task)!=pdPASS)ESP_LOGE("eyes","task allocation failed");
}
