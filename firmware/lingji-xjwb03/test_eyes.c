#include "eye_animation.h"
#include <assert.h>
#include <string.h>
int main(void){
 struct {uint8_t a;uint8_t f[EYE_BYTES];uint8_t b;} guard={.a=17,.b=29};
 uint8_t left[EYE_BYTES],right[EYE_BYTES];
 assert(EYE_CALM==9 && EYE_SQUINT==10 && EYE_HEART==11 && EYE_SPARK==12);
 assert(EYE_CHECK==13 && EYE_INBOX==14 && EYE_PUPIL_LEFT==15 && EYE_PUPIL_RIGHT==16);
 assert(EYE_MODE_COUNT==17);
 for(int m=0;m<EYE_MODE_COUNT;m++)for(unsigned t=0;t<12000;t+=17){eye_render(guard.f,0,m,t,t%1000);assert(guard.a==17 && guard.b==29);}
 for(int m=EYE_CALM;m<EYE_MODE_COUNT;m++){
  eye_render(left,0,m,0,0);eye_render(right,1,m,0,0);
  assert(!memcmp(left,right,EYE_BYTES));
  int nonempty=0;for(int i=0;i<EYE_BYTES;i++)nonempty|=left[i];
  assert(nonempty);
 }
 eye_render(left,0,EYE_WINK,2000,300);eye_render(right,1,EYE_WINK,2000,300);assert(memcmp(left,right,EYE_BYTES));
 eye_render(left,0,EYE_IDLE,0,0);eye_render(right,0,EYE_IDLE,1500,0);assert(memcmp(left,right,EYE_BYTES));
 return 0;
}
