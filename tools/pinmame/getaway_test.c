/* Private emulator instrumentation. Does not modify ROM, RAM or coil commands. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "getaway_test.h"

static int gt_initialized, gt_enabled;
static int gt_switch[119], gt_mechanism[65];
static unsigned long gt_reads[119], gt_changed_reads[119], gt_blocked[65], gt_writes;
static int gt_last_seen[119], gt_raw[5];
static double gt_last_read[119];
static struct { int state, next, timer, installed; } gt_balls[7];
static FILE *gt_trace;

static void gt_init(void) {
  if (gt_initialized) return;
  gt_initialized = 1;
  gt_enabled = getenv("GETAWAY_TEST_ENABLE") && !strcmp(getenv("GETAWAY_TEST_ENABLE"), "1");
  for (int i=0; i<119; i++) { gt_switch[i] = -1; gt_last_seen[i] = -1; }
  for (int i=0; i<65; i++) gt_mechanism[i] = -1;
  gt_raw[4] = 255; /* Fliptronics II is active low. */
  if (gt_enabled && getenv("GETAWAY_IO_TRACE")) {
    gt_trace = fopen(getenv("GETAWAY_IO_TRACE"), "wx");
    if (!gt_trace) { fprintf(stderr, "Cannot create private IO trace\n"); exit(91); }
    fprintf(gt_trace, "{\"kind\":\"header\",\"schema\":1,\"clock\":\"timer_get_time seconds\",\"all_cpu_writes\":true}\n");
    fflush(gt_trace);
  }
}

static int gt_valid_switch(int id) { return ((id/10>=1 && id/10<=8) || id/10==11) && id%10>=1 && id%10<=8; }

static int gt_column(int col, int raw) {
  gt_init();
  if (!gt_enabled) return raw;
  int result=raw;
  for (int row=0; row<8; row++) {
    int id=col*10+row+1, mask=1<<row;
    if (gt_switch[id]>=0) {
      int bit=(gt_switch[id] ? mask : 0) ^ (coreGlobals.invSw[col] & mask);
      result=(result & ~mask) | bit;
    }
    gt_reads[id]++;
    if ((raw ^ result) & mask) gt_changed_reads[id]++;
    gt_last_seen[id]=!!((result ^ coreGlobals.invSw[col]) & mask);
    gt_last_read[id]=timer_get_time();
  }
  return result;
}

int gwtest_switch_column(int select, int raw) {
  int col=1;
  if (select) { while (!(select & 1)) { select >>= 1; col++; } }
  return col>8 ? raw : gt_column(col,raw);
}

int gwtest_flipper_switches(int raw) { return gt_column(CORE_FLIPPERSWCOL,raw); }

int gwtest_mechanism_sol(int number, int commanded) {
  gt_init();
  if (!gt_enabled || number<1 || number>64 || gt_mechanism[number]<0) return commanded;
  if (!!commanded != gt_mechanism[number]) gt_blocked[number]++;
  return gt_mechanism[number];
}

void gwtest_raw_write(int offset, int data) {
  gt_init();
  if (!gt_enabled) return;
  int index;
  switch (offset) {
    case WPC_SOLENOID2: index=0; break; /* 3FE1, coils 1..8 */
    case WPC_SOLENOID4: index=1; break; /* 3FE3, coils 9..16 */
    case WPC_SOLENOID3: index=2; break; /* 3FE2, coils 17..24 */
    case WPC_SOLENOID1: index=3; break; /* 3FE0, coils 25..28 + GPIO */
    case WPC_FLIPPERS: index=4; break; /* 3FD4, active low */
    default: return;
  }
  gt_writes++;
  gt_raw[index]=data & 255;
  if (gt_trace)
    fprintf(gt_trace,"{\"kind\":\"write\",\"seq\":%lu,\"time\":%.9f,\"address\":%d,\"value\":%d,\"pc\":%u,\"bank\":%d}\n",
            gt_writes,timer_get_time(),offset+WPC_BASE,data&255,(unsigned)activecpu_get_pc(),wpc_data[WPC_ROMBANK]&63);
}

void gwtest_ball_update(int index, int state, int next, int timer, int installed) {
  gt_init();
  if (!gt_enabled || index<0 || index>=7) return;
  gt_balls[index].state=state; gt_balls[index].next=next; gt_balls[index].timer=timer;
  gt_balls[index].installed=installed;
}

int gwtest_set(const char *kind, int id, int value) {
  gt_init();
  if (!gt_enabled || value < -1 || value > 1) return -1;
  if (!strcmp(kind,"switch") && gt_valid_switch(id)) gt_switch[id]=value;
  else if (!strcmp(kind,"mechanism") && id>=1 && id<=64) gt_mechanism[id]=value;
  else return -1;
  if (gt_trace) {
    fprintf(gt_trace,"{\"kind\":\"fault\",\"time\":%.9f,\"target\":\"%s\",\"id\":%d,\"value\":%d}\n",timer_get_time(),kind,id,value);
    fflush(gt_trace);
  }
  return 0;
}

void gwtest_clear(void) {
  gt_init();
  for (int i=0;i<119;i++) gt_switch[i]=-1;
  for (int i=0;i<65;i++) gt_mechanism[i]=-1;
  if (gt_trace) { fprintf(gt_trace,"{\"kind\":\"clear_faults\",\"time\":%.9f}\n",timer_get_time()); fflush(gt_trace); }
}

char *gwtest_status(void) {
  gt_init();
  char *body=malloc(32768), *p=body;
  if (!body) return NULL;
  if (gt_trace) fflush(gt_trace);
  p+=sprintf(p,"{\"schema\":1,\"enabled\":%d,\"machine_ready\":%d,\"time\":%.9f,\"write_count\":%lu,\"raw_registers\":[%d,%d,%d,%d,%d],\"switches\":[",
             gt_enabled,coreData!=NULL,timer_get_time(),gt_writes,gt_raw[0],gt_raw[1],gt_raw[2],gt_raw[3],gt_raw[4]);
  int comma=0;
  for(int col=1;col<=11;col++) for(int row=1;row<=8;row++) {
    if(col==9 || col==10) continue;
    int id=col*10+row, physical=coreData ? !!core_getSw(id) : 0;
    p+=sprintf(p,"%s{\"id\":%d,\"forced\":%d,\"physical\":%d,\"effective\":%d,\"reads\":%lu,\"changed_reads\":%lu,\"last_seen\":%d,\"last_read_time\":%.9f}",
               comma++?",":"",id,gt_switch[id],physical,gt_switch[id]<0?physical:gt_switch[id],gt_reads[id],gt_changed_reads[id],gt_last_seen[id],gt_last_read[id]);
  }
  p+=sprintf(p,"],\"mechanisms\":["); comma=0;
  for(int i=1;i<=64;i++) if(gt_mechanism[i]>=0 || gt_blocked[i])
    p+=sprintf(p,"%s{\"id\":%d,\"forced_response\":%d,\"changed_observations\":%lu}",comma++?",":"",i,gt_mechanism[i],gt_blocked[i]);
  p+=sprintf(p,"],\"balls\":[");
  for(int i=0;i<7;i++)
    p+=sprintf(p,"%s{\"index\":%d,\"state\":%d,\"next\":%d,\"timer\":%d,\"installed\":%d}",i?",":"",i,gt_balls[i].state,gt_balls[i].next,gt_balls[i].timer,gt_balls[i].installed);
  p+=sprintf(p,"]}");
  return body;
}
