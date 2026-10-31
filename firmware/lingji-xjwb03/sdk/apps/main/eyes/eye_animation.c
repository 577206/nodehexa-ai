#include "eye_animation.h"
#include <math.h>
#include <string.h>
static float clamp(float x,float a,float b){return x<a?a:x>b?b:x;}
void eye_render(uint8_t out[EYE_BYTES],unsigned side,eye_mode_t mode,uint32_t now,uint32_t elapsed){
 memset(out,0,EYE_BYTES);
 float t=now*.001f, cx=64+10*sinf(t*.7f), cy=32, rx=29, ry=23;
 float open=clamp((float)(mode==EYE_OPEN?elapsed:now)/1100,0,1);
 if(mode==EYE_LISTEN){cx=64;ry=26;}
 if(mode==EYE_THINK){cx=64+15*sinf(t*1.4f);cy=26;ry=17;}
 if(mode==EYE_SPEAK){cx=64+7*sinf(t*2);ry=22+3*sinf(t*8);}
 if(mode==EYE_SURPRISE){rx=32;ry=29;cx=64;}
 if(mode==EYE_SLEEP)open*=.08f;
 unsigned blink=now%4300;
 if(blink>4000 && mode!=EYE_SLEEP)open*=fabsf((float)blink-4150)/150;
 if(mode==EYE_WINK && side==0 && elapsed<600)open*=fabsf((float)elapsed-300)/300;
 ry=fmaxf(1,ry*open);
 for(int y=0;y<EYE_HEIGHT;y++)for(int x=0;x<EYE_WIDTH;x++){
  float dx=(x-cx)/rx,dy=(y-cy)/ry;
  int on=dx*dx+dy*dy<=1;
  if(mode==EYE_HAPPY && ry>3)on=on && y<cy-ry*.1f && y>cy-ry*.55f-6*dx*dx;
  if(on)out[x+(y/8)*EYE_WIDTH]|=(uint8_t)(1u<<(y%8));
 }
}
