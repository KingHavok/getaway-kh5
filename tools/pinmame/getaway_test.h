#ifndef GETAWAY_TEST_H
#define GETAWAY_TEST_H
int gwtest_switch_column(int select, int raw);
int gwtest_flipper_switches(int raw);
int gwtest_mechanism_sol(int number, int commanded);
void gwtest_raw_write(int offset, int data);
void gwtest_ball_update(int index, int state, int next, int timer, int installed);
int gwtest_set(const char *kind, int id, int value);
void gwtest_clear(void);
char *gwtest_status(void);
#endif
