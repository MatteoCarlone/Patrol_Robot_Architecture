#! /usr/bin/env python

"""
.. module:: Controller
    :platform: Unix
    :synopsis: Python code that control the robot trough the via points generated by the planner

.. moduleauthor:: Matteo Carlone <matteo.carlone99@gmail.com>


Action:

    /armor_client
    motion/controller


This Node implement the controlling action that mainly consists in retrive the via points 
from the planner node and then simulate the movement by losing time while print the via points.
Once reached the final destination the current time and location associated with the robot is updated as the visited time of the room 
for the URGENT property estimation.

"""
#---Libraries---#

import rospy
from actionlib import SimpleActionServer
from exprolab_1.msg import ControlAction, ControlFeedback, ControlResult
from armor_api.armor_client import ArmorClient
from exprolab_1 import environment as env
import re
import time 

#--------------#

class ControllingAction(object):

    """

    Class representing the Controlling state of the Smach-State-Machine, which manage the robot's motion trough
    via poits sent by request from the action-client motion/controller in the fsm script.

    Methods
    ----------

    __init__(self)

        Initialization of parameters:

            client:ros_action_client
                Armor-Client to set-up the Ontology
            as:ros_action_server
                the server of the motion/controller action  

    execute_callback(self,goal)

        Server Callback of the action motion/controller requested from the fsm module to start up 
        the controlling action towards a target room.

        This Callback-Server simulate the robot's movement by printing its position in time. Once the robot reach 
        the target room some Ontology paramenters are updated: 

        * the robot location (isIn)
        * the time related to the robot (now)
        * the time in which the new target room is visited (visitedAt)

    """

    def __init__(self):

        self.client = ArmorClient('armor_client', 'reference')

        self._as = SimpleActionServer(env.ACTION_CONTROLLER,
            ControlAction,
            execute_cb=self.execute_callback,
            auto_start=False)

        self._as.start()

    def execute_callback(self, goal):
    
        print('\n###############\nCONTROLLING EXECUTION')

        # Check if the provided plan is processable. If not, this service will be aborted.
        if goal is None or goal.point_set is None or len(goal.point_set) == 0:
            print('No via points provided! This service will be aborted!')
            self._as.set_aborted()
            return

        # Initialise the `feedback`
        feedback = ControlFeedback()

        # loop to simulate robot moving in time 
        for point in goal.point_set:
            # Check that the client did not cancel this service.
            if self._as.is_preempt_requested():
                print('Service has been cancelled by the client!')
                # Actually cancel this service.
                self._as.set_preempted()
                return

            print('  ['+ str("%.2f"%point.x) +','+ str("%.2f"%point.y)+']', end = '\r')

            # update feedback
            feedback.reached_point = point
            self._as.publish_feedback(feedback)

            rospy.sleep(0.5)

        # Publish the results to the client.
        result = ControlResult()
        result.reached_point = feedback.reached_point
        self._as.set_succeeded(result)

        # map coordinates into locations
        starting_room = env.Map_C[str(goal.point_set[0].x) + ',' + str(goal.point_set[0].y)]
        reached_room = env.Map_C[str(result.reached_point.x) + ',' + str(result.reached_point.y)]

        # replace current robot location
        self.client.call('REPLACE', 'OBJECTPROP', 'IND', ['isIn', 'Robot1', reached_room, starting_room])

        # get current time instant 
        curr_time = int(time.time())

        # get time instant asscociated with the robot
        now = self.client.query.dataprop_b2_ind('now','Robot1')
        # format information
        now = re.search('"(.+?)"',str(now)).group(1)

        # replace robot time intant with the current one 
        self.client.call('REPLACE','DATAPROP','IND',['now', 'Robot1', 'Long' , str(curr_time)  , str(now) ])

        # get last time instant the robot visited the reached room
        visited_at = self.client.query.dataprop_b2_ind('visitedAt',reached_room)
        # format information
        visited_at = re.search('"(.+?)"',str(visited_at)).group(1)

        # replace the time instant the robot visited the reached room with the current one
        self.client.call('REPLACE','DATAPROP','IND',['visitedAt', reached_room, 'Long' , str(curr_time)  , str(visited_at) ])

        print('Reached Room: '+reached_room+ ' Coordinate: '+str(result.reached_point.x) + ' , ' + str(result.reached_point.y))
        print('Started from Room: '+ starting_room +' Coordinate: ' + str(goal.point_set[0].x) + ' , ' + str(goal.point_set[0].y))

        return  # Succeeded.

if __name__ == '__main__':
    # Initialise the node, its action server, and wait.   
    rospy.init_node(env.NODE_CONTROLLER, log_level=rospy.INFO)
    # Instantiate the node manager class and wait.
    server = ControllingAction()
    rospy.spin()