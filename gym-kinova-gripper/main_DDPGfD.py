import numpy as np
import torch
import gym
import argparse
import os, sys
os.environ['KMP_DUPLICATE_LIB_OK']='True'
import utils
#import TD3
#import OurDDPG
#import DDPG
import DDPGfD
import pdb
from tensorboardX import SummaryWriter
from ounoise import OUNoise
import pickle
import datetime
import csv
import time
from expert_data import store_saved_data_into_replay, GenerateExpertPID_JointVel, GenerateTestPID_JointVel, naive_check_grasp

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#device = torch.device('cpu')

def save_coordinates(x,y,filename):
    np.save(filename+"_x_arr", x)
    np.save(filename+"_y_arr", y)

# Runs policy for X episodes and returns average reward
def eval_policy(policy, env_name, seed, requested_shapes, requested_orientation, mode, eval_episodes=200, compare=False):
    num_success=0#[0,0]
    # Heatmap plot success/fail object coordinates
    seval_obj_posx = np.array([])
    feval_obj_posx = np.array([])
    seval_obj_posy = np.array([])
    feval_obj_posy = np.array([])
    total_evalx = np.array([])      # Total evaluation object coords
    total_evaly = np.array([])

    # match timesteps to expert and pre-training
    # max_num_timesteps = 150
    max_num_timesteps = 30

    # Folder to save heatmap coordinates
    evplot_saving_dir = "./eval_plots"
    if not os.path.isdir(evplot_saving_dir):
        os.mkdir(evplot_saving_dir)

    if compare:
        eval_env = gym.make(env_name)
        eval_env.seed(seed + 100)

        print("***Eval In Compare")
        # Generate randomized list of objects to select from
        eval_env.Generate_Latin_Square(eval_episodes,"eval_objects.csv",shape_keys=requested_shapes)
        ep_count = 0
        avg_reward = 0.0
        # step = 0
        for i in range(40):
            if i<23:
                x=(i)*0.005-0.055
                y=0.0
            elif i>=23:
                x=(i-23)*0.005-0.04
                y=0.0
            print('started pos', i)
            cumulative_reward = 0
            #eval_env = gym.make(env_name)
            state, done = eval_env.reset(start_pos=[x,y],env_name="eval_env",shape_keys=requested_shapes,hand_orientation=requested_orientation,mode=mode), False
            success=0
            # Sets number of timesteps per episode (counted from each step() call)
            #eval_env._max_episode_steps = 200
            eval_env._max_episode_steps = max_num_timesteps
            while not done:
                action = GenerateTestPID_JointVel(np.array(state),eval_env)
                state, reward, done, _ = eval_env.step(action)
                avg_reward += reward
                cumulative_reward += reward
                if reward > 25:
                    success=1
            num_success[1]+=success
            print('PID net reward:',cumulative_reward)
            state, done = eval_env.reset(start_pos=[x,y],env_name="eval_env",shape_keys=requested_shapes,hand_orientation=requested_orientation,mode=mode), False
            success=0
            cumulative_reward = 0
            # Sets number of timesteps per episode (counted from each step() call)
            #eval_env._max_episode_steps = 200
            eval_env._max_episode_steps = max_num_timesteps
            # Keep track of object coordinates
            obj_coords = eval_env.get_obj_coords()
            ep_count += 1
            print("***Eval episode: ",ep_count)

            timestep_count = 0
            while not done:
                timestep_count += 1
                action = policy.select_action(np.array(state[0:82]))
                state, reward, done, _ = eval_env.step(action)
                avg_reward += reward
                cumulative_reward += reward
                if reward > 25:
                    success=1
                # eval_env.render()
                # print(reward)
            # pdb.set_trace()
            print('Policy net reward:',cumulative_reward)
            num_success[0]+=success
            print("Eval timestep count: ",timestep_count)

            # Save initial object coordinate as success/failure
            x_val = (obj_coords[0])
            y_val = (obj_coords[1])
            x_val = np.asarray(x_val).reshape(1)
            y_val = np.asarray(y_val).reshape(1)

            if (success):
                seval_obj_posx = np.append(seval_obj_posx, x_val)
                seval_obj_posy = np.append(seval_obj_posy, y_val)
            else:
                feval_obj_posx = np.append(feval_obj_posx, x_val)
                feval_obj_posy = np.append(feval_obj_posy, y_val)

            total_evalx = np.append(total_evalx, x_val)
            total_evaly = np.append(total_evaly, y_val)

        avg_reward /= eval_episodes

        print("---------------------------------------")
        # print(f"Evaluation over {eval_episodes} episodes: {avg_reward:.3f}")
        print("Evaluation over {} episodes: {}".format(eval_episodes, avg_reward))
        print("---------------------------------------")

    else:
        eval_env = gym.make(env_name)
        eval_env.seed(seed + 100)

        # Generate randomized list of objects to select from
        eval_env.Generate_Latin_Square(eval_episodes,"eval_objects.csv",shape_keys=requested_shapes)

        avg_reward = 0.0
        # step = 0
        print("***Eval episodes total: ",eval_episodes)
        for i in range(eval_episodes):
            success=0
            #eval_env = gym.make(env_name)
            state, done = eval_env.reset(hand_orientation=requested_orientation,mode=args.mode,shape_keys=requested_shapes,env_name="eval_env"), False
            cumulative_reward = 0
            # Sets number of timesteps per episode (counted from each step() call)
            #eval_env._max_episode_steps = 200
            eval_env._max_episode_steps = max_num_timesteps
            print("***Eval episode: ", i)
            # Keep track of object coordinates
            obj_coords = eval_env.get_obj_coords()
            timestep_count = 0
            while not done:
                timestep_count += 1
                action = policy.select_action(np.array(state[0:82]))
                state, reward, done, _ = eval_env.step(action)
                avg_reward += reward
                cumulative_reward += reward
                if reward > 25:
                    success=1
                # eval_env.render()
                # print(reward)
            # pdb.set_trace()
            # print(cumulative_reward)
            num_success+=success
            print("Eval timestep count: ",timestep_count)

            # Save initial object coordinate as success/failure
            x_val = (obj_coords[0])
            y_val = (obj_coords[1])
            x_val = np.asarray(x_val).reshape(1)
            y_val = np.asarray(y_val).reshape(1)

            if(success):
                seval_obj_posx = np.append(seval_obj_posx,x_val)
                seval_obj_posy = np.append(seval_obj_posy,y_val)
            else:
                feval_obj_posx = np.append(feval_obj_posx,x_val)
                feval_obj_posy = np.append(feval_obj_posy,y_val)

            total_evalx = np.append(total_evalx, x_val)
            total_evaly = np.append(total_evaly, y_val)

        avg_reward /= eval_episodes

        print("---------------------------------------")
        # print(f"Evaluation over {eval_episodes} episodes: {avg_reward:.3f}")
        print("Evaluation over {} episodes: {}".format(eval_episodes, avg_reward))
        print("---------------------------------------")

    ret = [avg_reward, num_success, seval_obj_posx,seval_obj_posy,feval_obj_posx,feval_obj_posy,total_evalx,total_evaly]
    return ret


# def lift_hand(env_lift):
    # action = np.array([wrist_lift_velocity, finger_lift_velocity, finger_lift_velocity,
    #                    finger_lift_velocity])
    # next_state, reward, done, info = env_lift.step(action)
    # if done:
    #     # accumulate or replace?
    #     replay_buffer.replace(reward, done)

    # return done

def update_policy(evaluations, episode_num, num_episodes, writer, prob,
                  type_of_training, s_obj_posx, s_obj_posy, f_obj_posx, f_obj_posy, max_num_timesteps=30):

    # Initialize OU noise, added to action output from policy
    noise = OUNoise(4)
    noise.reset()
    expl_noise = OUNoise(4, sigma=0.001)
    expl_noise.reset()

    # Holds heatmap coordinates for eval plots
    seval_obj_posx = np.array([])   # Successful evaluation object coords
    seval_obj_posy = np.array([])
    feval_obj_posx = np.array([])   # Failed evaluation object coords
    feval_obj_posy = np.array([])
    total_evalx = np.array([])      # Total evaluation object coords
    total_evaly = np.array([])

    for _ in range(num_episodes):
        env = gym.make(args.env_name)

        # Max number of timesteps to match the expert replay grasp trials
        env._max_episode_steps = max_num_timesteps

        # Fill training object list using latin square
        if env.check_obj_file_empty("objects.csv"):
            env.Generate_Latin_Square(args.max_episode, "objects.csv", shape_keys=requested_shapes)
        state, done = env.reset(env_name="env", shape_keys=requested_shapes, hand_orientation=requested_orientation,
                                mode=args.mode), False

        prev_state_lift_check = None
        curr_state_lift_check = state


        noise.reset()
        expl_noise.reset()
        episode_reward = 0
        obj_coords = env.get_obj_coords()
        replay_buffer.add_episode(1)
        timestep = 0  # Timestep counter is only used for testing purposes

        print(type_of_training, episode_num)
        # print("replay_buffer.episodes_count: ", replay_buffer.episodes_count)
        check_for_lift = True
        ready_for_lift = False
        skip_num_ts = 6

        while not done:
            timestep = timestep + 1
            if timestep < skip_num_ts:
                wait_for_check = False
            else:
                wait_for_check = True
            ##make it modular
            ## If None, skip
            if prev_state_lift_check is None:
                f_dist_old = None
            else:
                f_dist_old = prev_state_lift_check[9:17]
            f_dist_new = curr_state_lift_check[9:17]

            if check_for_lift and wait_for_check:
                [ready_for_lift, _] = naive_check_grasp(f_dist_old, f_dist_new)

            # Store data in replay buffer
            ######### WITHOUT LIFT
            if not ready_for_lift:
                action = (
                        policy.select_action(np.array(state))
                        + np.random.normal(0, max_action * args.expl_noise, size=action_dim)
                ).clip(-max_action, max_action)
                # Perform action obs, total_reward, done, info
                next_state, reward, done, info = env.step(action)
                replay_buffer.add(state[0:82], action, next_state[0:82], reward, float(done))
                episode_reward += reward

            else:  # Make it happen in one time step
                action = np.array([wrist_lift_velocity, finger_lift_velocity, finger_lift_velocity,
                                   finger_lift_velocity])
                next_state, reward, done, info = env.step(action)
                if done:
                    # accumulate or replace?
                    replay_buffer.replace(reward, done)
                check_for_lift = False

            state = next_state

            # env.render()

            if info["lift_reward"] > 0:
                lift_success = True
            else:
                lift_success = False
            prev_state_lift_check = curr_state_lift_check
            curr_state_lift_check = state
            # print ("!!!!!!!!!!###########LIFT REWARD:#######!!!!!!!!!!!", info["lift_reward"])


        # print("timestep: ",timestep)
        replay_buffer.add_episode(0)
        # Train agent after collecting sufficient data:
        if episode_num > 10:
            for learning in range(100):
                actor_loss, critic_loss, critic_L1loss, critic_LNloss = policy.train(env._max_episode_steps,
                                                                                     expert_replay_buffer,
                                                                                     replay_buffer, prob)

                # Call if using batch replay buffer
                # actor_loss, critic_loss, critic_L1loss, critic_LNloss = policy.train_batch(replay_buffer,env._max_episode_steps)

        # Heatmap postion data, get starting object position
        x_val = obj_coords[0]
        y_val = obj_coords[1]
        x_val = np.asarray(x_val).reshape(1)
        y_val = np.asarray(y_val).reshape(1)
        if lift_success is True:
            s_obj_posx = np.append(s_obj_posx, x_val)
            s_obj_posy = np.append(s_obj_posy, y_val)
        else:
            f_obj_posx = np.append(f_obj_posx, x_val)
            f_obj_posy = np.append(f_obj_posy, y_val)

        # Evaluation and recording data for tensorboard
        if (episode_num + 1) % args.eval_freq == 0:
            eval_ret = eval_policy(policy, args.env_name, args.seed, requested_shapes, requested_orientation,
                                   mode=args.mode, eval_episodes=200)  # , compare=True)

            avg_reward = eval_ret[0]
            num_success = eval_ret[1]
            seval_obj_posx = np.append(seval_obj_posx, eval_ret[2])
            seval_obj_posy = np.append(seval_obj_posy, eval_ret[3])
            feval_obj_posx = np.append(feval_obj_posx, eval_ret[4])
            feval_obj_posy = np.append(feval_obj_posy, eval_ret[5])
            total_evalx = np.append(total_evalx, eval_ret[6])
            total_evaly = np.append(total_evaly, eval_ret[7])

            writer.add_scalar("Episode reward, Avg. 200 episodes", avg_reward, episode_num)
            writer.add_scalar("Actor loss", actor_loss, episode_num)
            writer.add_scalar("Critic loss", critic_loss, episode_num)
            writer.add_scalar("Critic L1loss", critic_L1loss, episode_num)
            writer.add_scalar("Critic LNloss", critic_LNloss, episode_num)
            evaluations.append(avg_reward)
            np.save("./results/%s" % (file_name), evaluations)
            print()

        # Save the x,y coordinates for object starting position (success vs failed grasp and lift)
        evplot_saving_dir = "./eval_plots"
        # Save coordinates every 1000 episodes
        if (episode_num + 1) % 1000 == 0:
            save_coordinates(seval_obj_posx, seval_obj_posy,
                             evplot_saving_dir + "/heatmap_eval_success" + str(episode_num))
            save_coordinates(feval_obj_posx, feval_obj_posy,
                             evplot_saving_dir + "/heatmap_eval_fail" + str(episode_num))
            save_coordinates(total_evalx, total_evaly, evplot_saving_dir + "/heatmap_eval_total" + str(episode_num))
            seval_obj_posx = np.array([])
            seval_obj_posy = np.array([])
            feval_obj_posx = np.array([])
            feval_obj_posy = np.array([])
            total_evalx = np.array([])
            total_evaly = np.array([])

        episode_num += 1
    return evaluations, episode_num, s_obj_posx, s_obj_posy, f_obj_posx, f_obj_posy


def pretrain_policy(tot_episodes):
    print("---- Pretraining ----")

    # Tensorboard writer for tracking loss and average reward
    pre_writer = SummaryWriter(logdir="./kinova_gripper_strategy/{}_{}/".format("pretrtain_" + args.policy_name, args.tensorboardindex))

    pretrain_model_path = saving_dir + "/pre_DDPGfD_kinovaGrip_{}".format(datetime.datetime.now().strftime("%m_%d_%y_%H%M"))

    # Save the x,y coordinates for object starting position (success vs failed grasp and lift)
    pretrain_saving_dir = "./pretrain_plots"
    if not os.path.isdir(pretrain_saving_dir):
        os.mkdir(pretrain_saving_dir)

    prob_exp = 0.8

    ###HERE####
    # state, done = env.reset(env_name="env",shape_keys=requested_shapes,hand_orientation=requested_orientation,
    # mode=args.mode), False
    # if not os.path.exists("./results"): # Stores average reward of policy from evaluations list
    #     os.makedirs("./results")
    evals = []

    curr_episode = 0         # Counts number of episodes done within training

    # Heatmap initial object coordinates for training
    s_pretrain_obj_posx = np.array([])  # Successful initial object coordinates: training
    s_pretrain_obj_posy = np.array([])
    f_pretrain_obj_posx = np.array([])  # Failed initial object coordinates: training
    f_pretrain_obj_posy = np.array([])
    ###########

    evals, curr_episode, s_pretrain_obj_posx,  s_pretrain_obj_posy, f_pretrain_obj_posx,  f_pretrain_obj_posy = \
        update_policy(evals, curr_episode, tot_episodes, pre_writer, prob_exp, "PRE", s_pretrain_obj_posx,
                      s_pretrain_obj_posy, f_pretrain_obj_posx, f_pretrain_obj_posy)

    train_totalx = np.append(s_pretrain_obj_posx, f_pretrain_obj_posx)
    train_totaly = np.append(s_pretrain_obj_posy, f_pretrain_obj_posy)

    # Save object postions from training
    print("Success train num: ",len(s_pretrain_obj_posx))
    print("Fail train num: ", len(f_pretrain_obj_posx))
    print("Total train num: ", len(train_totalx))
    save_coordinates(s_pretrain_obj_posx,s_pretrain_obj_posy,pretrain_saving_dir+"/heatmap_train_success_new")
    save_coordinates(f_pretrain_obj_posx,f_pretrain_obj_posy,pretrain_saving_dir+"/heatmap_train_fail_new")
    save_coordinates(train_totalx,train_totaly,pretrain_saving_dir+"/heatmap_train_total_new")

    print("Saving into {}".format(pretrain_model_path))
    policy.save(pretrain_model_path)

    return pretrain_model_path


def train_policy(tot_episodes):
    trplot_saving_dir = "./train_plots"
    if not os.path.isdir(trplot_saving_dir):
       os.mkdir(trplot_saving_dir)
    model_save_path = saving_dir + "/DDPGfD_kinovaGrip_{}".format(datetime.datetime.now().strftime("%m_%d_%y_%H%M"))
    # Initialize SummaryWriter
    tr_writer = SummaryWriter(logdir="./kinova_gripper_strategy/{}_{}/".format(args.policy_name, args.tensorboardindex))
    tr_prob = 0.8
    tr_ep = int(tot_episodes/4)
    ###HERE####
    # state, done = env.reset(env_name="env",shape_keys=requested_shapes,hand_orientation=requested_orientation,
    # mode=args.mode), False
    if not os.path.exists("./results"): # Stores average reward of policy from evaluations list
        os.makedirs("./results")
    evals = []
    curr_episode = 0         # Counts number of episodes done within training
    red_expert_prob= 0.1

    # Heatmap initial object coordinates for training
    s_train_obj_posx = np.array([])  # Successful initial object coordinates: training
    s_train_obj_posy = np.array([])
    f_train_obj_posx = np.array([])  # Failed initial object coordinates: training
    f_train_obj_posy = np.array([])
    ###########
    for i in range(4):
        evals, curr_episode, s_train_obj_posx,  s_train_obj_posy, f_train_obj_posx,  f_train_obj_posy =\
            update_policy(evals, curr_episode, tr_ep, tr_writer, tr_prob, "TRAIN", s_train_obj_posx, s_train_obj_posy,
                          f_train_obj_posx, f_train_obj_posy)
        tr_prob = tr_prob - red_expert_prob

    train_totalx = np.append(s_train_obj_posx, f_train_obj_posx)
    train_totaly = np.append(s_train_obj_posy, f_train_obj_posy)

    # Save object postions from training
    print("Success train num: ",len(s_train_obj_posx))
    print("Fail train num: ", len(f_train_obj_posx))
    print("Total train num: ", len(train_totalx))
    save_coordinates(s_train_obj_posx,s_train_obj_posy, trplot_saving_dir+"/heatmap_train_success_new")
    save_coordinates(f_train_obj_posx,f_train_obj_posy, trplot_saving_dir+"/heatmap_train_fail_new")
    save_coordinates(train_totalx,train_totaly, trplot_saving_dir+"/heatmap_train_total_new")

    print("Saving into {}".format(model_save_path))
    policy.save(model_save_path)

    return model_save_path

if __name__ == "__main__":

    wrist_lift_velocity = 0.6
    min_velocity = 0.5
    finger_lift_velocity = min_velocity

    parser = argparse.ArgumentParser()
    parser.add_argument("--policy_name", default="DDPGfD")				# Policy name
    parser.add_argument("--env_name", default="gym_kinova_gripper:kinovagripper-v0")			# OpenAI gym environment name
    parser.add_argument("--seed", default=2, type=int)					# Sets Gym, PyTorch and Numpy seeds
    parser.add_argument("--start_timesteps", default=100, type=int)		# How many time steps purely random policy is run for
    parser.add_argument("--eval_freq", default=100, type=float)			# How often (time steps) we evaluate
    parser.add_argument("--max_timesteps", default=1e6, type=int)		# Max time steps to run environment for
    parser.add_argument("--max_episode", default=15000, type=int)		# Max time steps to run environment for
    parser.add_argument("--save_models", action="store_true")			# Whether or not models are saved
    parser.add_argument("--expl_noise", default=0.1, type=float)		# Std of Gaussian exploration noise
    parser.add_argument("--batch_size", default=250, type=int)			# Batch size for both actor and critic
    parser.add_argument("--discount", default=0.995, type=float)			# Discount factor
    parser.add_argument("--tau", default=0.0005, type=float)				# Target network update rate
    parser.add_argument("--policy_noise", default=0.01, type=float)		# Noise added to target policy during critic update
    parser.add_argument("--noise_clip", default=0.05, type=float)		# Range to clip target policy noise
    parser.add_argument("--policy_freq", default=2, type=int)			# Frequency of delayed policy updates
    parser.add_argument("--tensorboardindex", default="new")	# tensorboard log name
    parser.add_argument("--model", default=1, type=int)	# save model index
    parser.add_argument("--expert_replay_size", default=20000, type=int)	# Number of episode for loading expert trajectories
    parser.add_argument("--saving_dir", default="new")	# Number of episode for loading expert trajectories
    parser.add_argument("--shapes", default='CubeS', action='store', type=str) # Requested shapes to use (in format of object keys)
    parser.add_argument("--hand_orientation", action='store', type=str) # Requested shapes to use (in format of object keys)
    parser.add_argument("--mode", action='store', type=str, default="train") # Mode to run experiments with: (expert, pre-train, train, rand_train, test)
    parser.add_argument("--agent_replay_size", default=10100, type=int) # Maximum size of agent's replay buffer

    args = parser.parse_args()

    """ Setup the environment, state, and action space """

    file_name = "%s_%s_%s" % (args.policy_name, args.env_name, str(args.seed))
    print("---------------------------------------")
    print("Settings: {file_name}")
    print("---------------------------------------")

    # Make initial environment
    env = gym.make(args.env_name)

    # Set seeds for randomization
    env.seed(args.seed)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    # Set dimensions for state and action spaces - policy initialization
    state_dim = 82  # State dimension dependent on the length of the state space
    action_dim = env.action_space.shape[0]
    max_action = float(env.action_space.high[0])
    max_action_trained = env.action_space.high  # a vector of max actions
    n = 5   # n step look ahead for the policy

    ''' Set values from command line arguments '''
    requested_shapes = args.shapes                   # Sets list of desired objects for experiment
    requested_shapes = requested_shapes.split(',')
    requested_orientation = args.hand_orientation   # Set the desired hand orientation (normal or random)
    expert_replay_size = args.expert_replay_size    # Number of expert episodes for expert the replay buffer
    agent_replay_size = args.agent_replay_size      # Maximum number of episodes to be stored in agent replay buffer
    # max_num_timesteps = 150     # Maximum number of time steps within an episode
    max_num_timesteps = 30     # Maximum number of time steps within an episode

    # Fill pre-training object list using latin square method
    env.Generate_Latin_Square(args.max_episode,"objects.csv", shape_keys=requested_shapes)

    kwargs = {
        "state_dim": state_dim,
        "action_dim": action_dim,
        "max_action": max_action,
        "n": n,
        "discount": args.discount,
        "tau": args.tau,
        # "trained_model": "data_cube_5_trained_model_10_07_19_1749.pt"
    }

    ''' Initialize policy '''
    if args.policy_name == "DDPGfD":
        policy = DDPGfD.DDPGfD(**kwargs)
    else:
        print("No such policy")
        raise ValueError

    # Print variables set based on command line input
    print("Policy: ", args.policy_name)
    print("Requested_shapes: ",requested_shapes)
    print("Requested Hand orientation: ", requested_orientation)

    ''' Select replay buffer type
    # Replay buffer that can use multiple n-steps
    #replay_buffer = utils.ReplayBuffer_VarStepsEpisode(state_dim, action_dim, expert_replay_size)
    #replay_buffer = utils.ReplayBuffer_NStep(state_dim, action_dim, expert_replay_size)

    # Replay buffer that samples only one episode
    #replay_buffer = utils.ReplayBuffer_episode(state_dim, action_dim, env._max_episode_steps, args.expert_replay_size, args.max_episode)
    #replay_buffer = GenerateExpertPID_JointVel(args.expert_replay_size, replay_buffer, False)
    '''

    # Initialize Queue Replay Buffer: replay buffer manages its size like a queue, popping off the oldest episodes
    replay_buffer = utils.ReplayBuffer_Queue(state_dim, action_dim, agent_replay_size)

    # Default expert pid file path
    expert_file_path = "./expert_replay_data/Expert_data_01_16_21_2315/"

    # Default pre-trained policy file path
    pretrain_model_save_path = "./policies/new/pre_DDPGfD_kinovaGrip_01_14_21_0100"

    # Create directory to hold trained policy
    saving_dir = "./policies/" + args.saving_dir
    if not os.path.isdir(saving_dir):
        os.mkdir(saving_dir)


    # Determine replay buffer/policy function calls based on mode (expert, pre-train, train, rand_train, test)
    if args.mode == "expert":
        print("MODE: Expert")
        # Initialize expert replay buffer, then generate expert pid data to fill it
        expert_replay_buffer = utils.ReplayBuffer_Queue(state_dim, action_dim, expert_replay_size)
        # expert_replay_buffer, expert_file_path = GenerateExpertPID_JointVel(expert_replay_size, expert_replay_buffer, True)
        expert_replay_buffer, expert_file_path = GenerateExpertPID_JointVel(10, expert_replay_buffer, True)        
        print("expert_file_path: ",expert_file_path, "\n", expert_replay_buffer)
        quit()
    # Pre-train policy using expert data, save pre-trained policy for use in training
    elif args.mode == "pre-train":
        print("MODE: Pre-train")
        num_updates = 10#2000 #10000 # Number of expert pid grasp trials used to update policy
        # Load expert data from saved expert pid controller replay buffer
        expert_replay_buffer = store_saved_data_into_replay(replay_buffer, expert_file_path)
        print ("SIZE:", expert_replay_buffer.size)
        # Pre-train policy based on expert data
        pretrain_model_save_path = pretrain_policy(num_updates)
        print("pretrain_model_save_path: ",pretrain_model_save_path)
        quit()
    elif args.mode == "train":
        print("MODE: Train (w/ pre-trained policy")
        # Load pre-trained policy
        # expert_replay_buffer = store_saved_data_into_replay(replay_buffer, expert_file_path)
        # Initialize expert replay buffer, then generate expert pid data to fill it
        expert_replay_buffer = utils.ReplayBuffer_Queue(state_dim, action_dim, expert_replay_size)
        # expert_replay_buffer, expert_file_path = GenerateExpertPID_JointVel(expert_replay_size, expert_replay_buffer, True)
        expert_replay_buffer, expert_file_path = GenerateExpertPID_JointVel(15, expert_replay_buffer, True)
        print("expert_file_path: ",expert_file_path, "\n", expert_replay_buffer)
        num_updates = 20
        pretrain_model_save_path = pretrain_policy(num_updates)
        print("pretrain_model_save_path: ",pretrain_model_save_path)
        # Load Pre-Trained policy
        policy.load(pretrain_model_save_path)
        print("LOADED THE Pre-trained POLICY")
        tot_num_episodes = 44#args.max_episode
        train_policy(tot_num_episodes)

    elif args.mode == "rand_train":
        print("MODE: Train (Random init policy)")
        expert_replay_size = 0
        expert_replay_buffer = None
    elif args.mode == "test":
        print("MODE: Test")
        # TBD
    else:
        print("Invalid mode input")
        quit()


