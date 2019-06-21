#!/usr/bin/env python3

"""classic Acrobot task"""
import numpy as np
from numpy import sin, cos, pi
from gym import core, spaces
from gym.utils import seeding
import rospy
import math
from train.srv import environment
from CheckCollision import CheckCollision
# from CheckCollision_tensor import CheckCollision
# from vacuum_cmd_msg.srv import VacuumCmd
class Test(core.Env):

    dt = .2

    LINK_LENGTH_1 = 1.  # [m]
    LINK_LENGTH_2 = 1.  # [m]
    LINK_MASS_1 = 1.  #: [kg] mass of link 1
    LINK_MASS_2 = 1.  #: [kg] mass of link 2
    LINK_COM_POS_1 = 0.5  #: [m] position of the center of mass of link 1
    LINK_COM_POS_2 = 0.5  #: [m] position of the center of mass of link 2
    LINK_MOI = 1.  #: moments of inertia for both links

    MAX_VEL_1 = 2.
    MAX_VEL_2 = 2.
    MAX_VEL_3 = 2.

    ACTION_VEC_TRANS = 1/180
    ACTION_ORI_TRANS = 1/30
    ACTION_PHI_TRANS = 1/30

    NAME = ['/right_arm', '/left_arm', '/right_arm']

    torque_noise_max = 0.

    #: use dynamics equations from the nips paper or the book
    book_or_nips = "book"
    action_arrow = None
    domain_fig = None
    actions_num = 8

    def __init__(self, name):
        self.__name = self.NAME[name%2]
        self.__obname = self.NAME[name%2 + 1]
        self.viewer = None

        high = np.array([1.,1.,1.,1.,1.,1.,1.,1.,
                         1.,1.,1.,1.,1.,1.,1.,1.,
                         1.,1.,1.,1.,1.,1.,1.,1.,
                         0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,
                         0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,
                         0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.])
        low = -high # gx,gy,gz,ga,gb,gc,gd,gf,
                    #ox,oy,oz,oa,ob,oc,od,of,
                    # 1xyz,2xyz,4xyz,6xyz,
                    # joint_angle, limit
        self.observation_space = spaces.Box(low=low, high=high, dtype=np.float32)
        self.action_space = spaces.Discrete(8)
        self.state = []
        self.action = []
        self.cmd = []
        self.point = []
        self.goal = []
        self.goal_pos = []
        self.goal_quat = []
        self.goal_phi = 0
        self.old = []
        self.old_pos = []
        self.old_quat = []
        self.old_phi = 0
        self.joint_pos = []
        self.joint_angle = []
        self.limit = []
        # self.dis_pos
        self.cc = CheckCollision()
        self.collision = False
        self.range_cnt = 0.2
        self.s_cnt = 0
        self.seed()
        self.reset()
        
    def get_state_client(self, cmd, name):
        ik_service = name+'/train_env'
        try:
            rospy.wait_for_service(ik_service, timeout=1.)
        except rospy.ROSException as e:
            rospy.logwarn('wait_for_service timeout')
            self.get_state_client(cmd, name)
            
        client = rospy.ServiceProxy(
            ik_service,
            environment
        )
        # res = client(cmd)
        res = client.call(cmd)
        return res

    def env_reset_client(self, cmd, name):
        reset_service = name+'/env_reset'
        try:
            rospy.wait_for_service(reset_service, timeout=1.)
        except rospy.ROSException as e:
            rospy.logwarn('wait_for_service timeout')
            self.env_reset_client(cmd, name)
            
        client = rospy.ServiceProxy(
            reset_service,
            environment
        )
        # res = client(cmd)
        res = client.call(cmd)
        return res

    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def reset(self):
        self.goal = self.set_goal()
        self.old, self.joint_pos[:12], self.joint_pos[12:24], self.joint_pos[24:27],self.joint_angle, self.limit = self.set_old()
        self.state = np.append(self.goal, self.old)
        self.state = np.append(self.state, np.subtract(self.goal, self.old))
        self.state = np.append(self.state, self.joint_pos)
        self.state = np.append(self.state, self.joint_angle)
        self.state = np.append(self.state, self.limit)
        self.dis_pos = np.linalg.norm(np.subtract(self.goal[:3], self.old[:3]))
        self.dis_ori = np.linalg.norm(np.subtract(self.goal[3:7], self.old[3:7]))
        self.dis_phi = math.fabs(self.goal[7] - self.old[7])
        r_ori = (self.dis_ori/self.dis_pos)/6
        r_phi = (self.dis_phi/self.dis_pos)/6
        r_pos = 1 if self.dis_pos > 0.04 else self.dis_pos*20+0.2
        move_rate = [r_pos, r_ori, r_phi]
        self.state = np.append(self.state, move_rate)
        self.collision = False
        return self.state

    def set_goal(self):
        self.goal = self.np_random.uniform(low=0., high=self.range_cnt, size=(8,))
        # print('self.goal = ', self.goal)
        self.goal[0] = 0
        self.goal = np.append(self.goal, self.range_cnt)
        res = self.env_reset_client(self.goal, self.__name)
        if res.success:
            return res.state
        else:
            return self.set_goal()

    def set_old(self):
        self.old = self.np_random.uniform(low=0., high=self.range_cnt, size=(8,))
        # print('self.old = ', self.old)
        self.old[0] = 0
        self.old = np.append(self.old, self.range_cnt)
        res = self.env_reset_client(self.old, self.__name)
        res_ = self.env_reset_client([0], self.__obname)
        old_pos = []
        old_pos = np.append(old_pos, res.state)
        if np.linalg.norm(old_pos[:3] - self.goal[:3]) > 0.1:
            return res.state, res.joint_pos, res_.joint_pos,[res_.state[0], res_.state[1], res_.state[2]], res.joint_angle, res.limit
        else:
            return self.set_old()

    def step(self, a):
        s = self.state
        action_vec = a[:3]*self.ACTION_VEC_TRANS
        action_ori = a[3:7]*self.ACTION_ORI_TRANS
        action_phi = a[7]*np.pi*self.ACTION_PHI_TRANS
        self.action = np.append(action_vec, action_ori)
        self.action = np.append(self.action, action_phi)
        self.cmd = np.add(s[8:16], self.action)
        self.cmd[3:7] /= np.linalg.norm(self.cmd[3:7])
        res = self.get_state_client(self.cmd, self.__name)
        res_ = self.get_state_client([0], self.__obname)
        if res.success:
            self.old, self.joint_pos[:12], self.joint_angle = res.state, res.joint_pos, res.joint_angle
            self.joint_pos[12:24] = res_.joint_pos
            self.joint_pos[24:27] = [res_.state[0], res_.state[1], res_.state[2]]
            s = np.append(self.goal, self.old)
            s = np.append(s, np.subtract(self.goal, self.old))
            s = np.append(s, self.joint_pos)
            s = np.append(s, self.joint_angle)
            s = np.append(s, self.limit)
            self.dis_pos = np.linalg.norm(self.goal[:3] - s[8:11])
            self.dis_ori = np.linalg.norm(self.goal[3:7] - s[11:15])
            self.dis_phi = math.fabs(self.goal[7] - s[15])
            self.dis_state = np.linalg.norm(self.goal - s[8:16])
            r_ori = (self.dis_ori/self.dis_pos)/6
            r_phi = (self.dis_phi/self.dis_pos)/6
            r_pos = 1 if self.dis_pos > 0.04 else self.dis_pos*20+0.2
            move_rate = [r_pos, r_ori, r_phi]
            s = np.append(s, move_rate)
   
        terminal = self._terminal(s, res.success)
        reward = self.get_reward(s, res.success, terminal)    
        self.state = s
        return self.state, reward, terminal, 1

    def _terminal(self, s, ik_success):
        if ik_success:
            linkPosM = np.array(self.joint_pos[0:12])
            linkPosS = np.array(self.joint_pos[12:27])
            linkPosM = np.append(linkPosM, s[8:11])
            linkPosM = np.append([0.,0.,-0.8], linkPosM)
            linkPosS = np.append([0.,0.,-0.8], linkPosS)
            linkPosM = linkPosM.reshape(6,3)
            linkPosS = linkPosS.reshape(6,3)
            alarm = self.cc.checkCollision(linkPosM, linkPosS)
            alarm_cnt = 0
            for i in alarm:
                alarm_cnt += i
            if alarm_cnt>0:
                self.collision = True

            if (self.dis_pos < 0.015 and self.dis_ori < 0.1 and self.dis_phi < 0.1):
                self.s_cnt += 1
                self.range_cnt = self.range_cnt + 0.003 if self.range_cnt < 0.9 else 0.9
                print('ssssssuuuuuuccccccccceeeeeeeesssssssssss' , self.s_cnt)
                return True
            else:
                return False
        else:
            return False
        

    def get_reward(self, s, ik_success, terminal):
        goal_vec = self.goal[:3] - self.state[8:11]
        goal_ori = self.goal[3:7]- self.state[11:15]
        goal_phi = self.goal[7]  - self.state[15]
        # old_dis = np.linalg.norm(self.goal - self.state[8:16])
        cos_vec = np.dot(self.action[:3],  goal_vec)/(np.linalg.norm(self.action[:3]) *np.linalg.norm(goal_vec))
        cos_ori = np.dot(self.action[3:7], goal_ori)/(np.linalg.norm(self.action[3:7])*np.linalg.norm(goal_ori))
       
        goal_dis = np.linalg.norm(self.dis_pos)
        a_leng = np.linalg.norm(self.action[:3]/self.ACTION_VEC_TRANS)

        reward = 0

        if terminal:
            if not self.collision:
                reward += 100
            else:
                reward += -100
            return reward
        if not ik_success:
            return -100
        if a_leng<0.2 or a_leng>2:
            reward += -2
        
        if cos_vec > np.math.cos(30*np.pi/180):
            r = (cos_vec*cos_vec*cos_vec)/(goal_dis**0.5)
            reward += 10 if r > 10 else r
        elif self.dis_pos > 0.05:
            r = -goal_dis/(cos_vec+1)
            reward += -2 if r<-2 else r
       
        if cos_ori > np.math.cos(30*np.pi/180):
            reward += 3
        elif self.dis_ori > 0.15:
            reward += -2
        # if cos_ori < np.math.cos(60*np.pi/180):
        #     reward += -1
        if goal_phi*self.action[7] > 0:
            reward += 2
        elif self.dis_phi > 0.15:
            reward += -1
        if self.dis_pos < 0.05 or self.dis_ori < 0.15 or self.dis_phi < 0.15:
            reward += 5
        return reward/5


        #===============================================================================
        # if terminal:
        #     return 10
        # if not ik_success:
        #     return -10
        # if self.collision:
        #     return -10

        # if a_leng<0.2 or a_leng>2:
        #     reward += -1
        # if cos_vec > np.math.cos(10*np.pi/180):
        #     r = (cos_vec*cos_vec*cos_vec)
        #     reward += 2*r
        # elif self.dis_state < old_dis:
        #     reward += 1
       
        # if self.dis_pos < 0.05 or self.dis_ori < 0.15 or self.dis_phi < 0.15:
        #     reward += 2
        # reward /= 2
        # reward = 1 if reward>1 else reward
        # reward = -1 if reward < -1 else reward
        # return reward
        #==================================================================================


