#define RED 0
#define BLUE 1
#define TEAM_OFFSET 2
#define DEBUG true

#define MAX_BUFFER_SIZE 750 //MATH: (1/WEBTV_POSITION_UPDATE_RATE)*(MAX_TV_DELAY) + MAX_POSSIBLE_ADDITIONAL_EVENTS
                            //the maximum possible additional events is an (overly generous) educated guess at the number of events that could occur @ max tv_delay (90s)

#define WEBTV_POSITION_UPDATE_RATE 0.25 /*rate at which position packets are added to the buffer. MAKE SURE TO BE SLOWER THAN THE PROCESS TIMER,
                                       ELSE YOU WILL GET MULTIPLE POSITION UPDATES IN THE SAME PROCESSING FRAME (BAD) AND WASTE RESOURCES*/
#define WEBTV_BUFFER_PROCESS_RATE 0.12 /*tf2 tickrate process time is 66.66 updates/sec = update every 15 ms. 
                                        we process the buffer ~5 times slower (120ms). this will send position updates virtually instantly */

#define BITMASK_DAMAGE_TAKEN 1 //bit value of DAMAGE_TAKEN                                
#define BITMASK_DAMAGE_DEALT 2
#define BITMASK_HEALING 4
#define BITMASK_ITEM_PICKUP 8