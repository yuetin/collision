/*******************************************************************************
* Copyright 2018 ROBOTIS CO., LTD.
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
*     http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*******************************************************************************/

#ifndef MANIPULATOR_KINEMATICS_DYNAMICS_LINK_DATA_H_
#define MANIPULATOR_KINEMATICS_DYNAMICS_LINK_DATA_H_

#include "robotis_math/robotis_math.h"

namespace robotis_manipulator_h
{

class LinkData
{
public:
  LinkData();
  ~LinkData();

  std::string name_;

  int parent_;
  int sibling_;
  int child_;

  double mass_;

  Eigen::MatrixXd relative_position_;
  Eigen::MatrixXd joint_axis_;
  Eigen::MatrixXd center_of_mass_;
  Eigen::MatrixXd inertia_;
  Eigen::VectorXd euler;

  double joint_limit_max_;
  double joint_limit_min_;
  double train_limit_max_;
  double train_limit_min_;

  double joint_angle_;
  double joint_velocity_;
  double joint_acceleration_;
  double slide_position_;  //new
  double phi_; //new
  double mov_speed_;  //new
  bool singularity_;

  Eigen::MatrixXd position_;
  Eigen::MatrixXd orientation_;   //////////////////////////changed!!!!!!!!!!!!!!!!!
  Eigen::MatrixXd transformation_;
};

}

#endif /* MANIPULATOR_KINEMATICS_DYNAMICS_LINK_DATA_H_ */
