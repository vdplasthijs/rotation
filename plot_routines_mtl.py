# @Author: Thijs L van der Plas <thijs>
# @Date:   2021-04-14
# @Email:  thijs.vanderplas@dtc.ox.ac.uk
# @Last modified by:   thijs
# @Last modified time: 2021-04-14

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as patches
from mpl_toolkits.axes_grid1 import make_axes_locatable
from mpl_toolkits.axes_grid1.colorbar import colorbar as mpl_colorbar
import seaborn as sns
import pickle, os, sys, copy
import scipy.stats
import sklearn.decomposition
import bptt_rnn_mtl as bpm
import rot_utilities as ru
import pandas as pd
from cycler import cycler
from tqdm import tqdm
## Create list with standard colors:
color_dict_stand = {}
for ii, x in enumerate(plt.rcParams['axes.prop_cycle']()):
    color_dict_stand[ii] = x['color']
    if ii > 8:
        break  # after 8 it repeats (for ever)
plt.rcParams['axes.prop_cycle'] = cycler(color=sns.color_palette('colorblind'))

time_labels = ['0', '0', r'$S_1$', r'$S_1$', '0', '0', r'$S_2$', r'$S_2$', '0', '0', 'G', 'G', '0', '0']
time_labels_blank = ['' if x == '0' else x for x in time_labels]
input_vector_labels = ['0', r'$A_1$', r'$A_2$', r'$B_1$', r'$B_2$', 'G']
output_vector_labels = input_vector_labels + [r'$M_1$', r'$M_2$']

pred_only_colour = [67 / 255, 0, 0]
spec_only_colour = [207 / 255, 143 / 255, 23 / 255]
pred_spec_colour = [73 / 255, 154 / 255, 215 / 255]

def set_fontsize(font_size=12):
    plt.rcParams['font.size'] = font_size
    plt.rcParams['axes.autolimit_mode'] = 'data' # default: 'data'
    params = {'legend.fontsize': font_size,
             'axes.labelsize': font_size,
             'axes.titlesize': font_size,
             'xtick.labelsize': font_size,
             'ytick.labelsize': font_size}
    plt.rcParams.update(params)

def despine(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    return ax

def opt_leaf(w_mat, dim=0):
    '''create optimal leaf order over dim, of matrix w_mat. if w_mat is not an
    np.array then its assumed to be a RNN layer. see also: https://docs.scipy.org/doc/scipy/reference/generated/scipy.cluster.hierarchy.optimal_leaf_ordering.html#scipy.cluster.hierarchy.optimal_leaf_ordering'''
    if type(w_mat) != np.ndarray:  # assume it's an rnn layer
        w_mat = [x for x in w_mat.parameters()][0].detach().numpy()
    assert w_mat.ndim == 2
    if dim == 1:  # transpose to get right dim in shape
        w_mat = w_mat.T
    dist = scipy.spatial.distance.pdist(w_mat, metric='euclidean')  # distanc ematrix
    link_mat = scipy.cluster.hierarchy.ward(dist)  # linkage matrix
    opt_leaves = scipy.cluster.hierarchy.leaves_list(scipy.cluster.hierarchy.optimal_leaf_ordering(link_mat, dist))
    return opt_leaves

def plot_split_perf(rnn_name=None, rnn_folder=None, ax_top=None, ax_bottom=None,
                    normalise_start=False,
                    plot_top=True, plot_bottom=True, list_top=None, lw=3, plot_total=True,
                    label_dict_keys = {x: x for x in ['dmc', 'dms', 'pred', 'S2', 'G', 'G1', 'G2',
                                                            '0', '0_postS1', '0_postS2', '0_postG']},
                    linestyle_custom_dict={}, colour_custom_dict={},
                    plot_std=True, plot_indiv=False):
    if normalise_start:
        print('Normalising loss functions')
    if ax_top is None and plot_top:
        ax_top = plt.subplot(211)
    if ax_bottom is None and plot_bottom:
        ax_bottom = plt.subplot(212)
    if rnn_folder is None:
        list_rnns = [rnn_name]
    else:
        list_rnns = [x for x in os.listdir(rnn_folder) if x[-5:] == '.data']


    # print(label_dict_keys)
    n_rnn = len(list_rnns)
    for i_rnn, rnn_name in enumerate(list_rnns):
        rnn = ru.load_rnn(rnn_name=os.path.join(rnn_folder, rnn_name))
        # if 'dmc' in rnn.test_loss_split.keys():
            # print(rnn.test_loss_split['dmc'][-3:])
        if i_rnn == 0:
            # print(rnn.info_dict['pred_loss_function'])
            n_tp = rnn.info_dict['n_epochs']
            # if 'simulated_annealing' in list(rnn.info_dict.keys()) and rnn.info_dict['simulated_annealing']:
            #     pass
            # else:
            #     assert n_tp == rnn.info_dict['n_epochs']  # double check and  assume it is the same for all rnns in rnn_folder\
            conv_dict = {key: np.zeros((n_rnn, n_tp)) for key in rnn.test_loss_split.keys()}
            if plot_total:
                conv_dict['pred_sep'] = np.zeros((n_rnn, n_tp))
        else:
            assert rnn.info_dict['n_epochs'] == n_tp
        for key, arr in rnn.test_loss_split.items():
            # if key != 'pred':
            conv_dict[key][i_rnn, :] = arr.copy()
        if plot_total:
            conv_dict['pred_sep'][i_rnn, :] = np.sum([conv_dict[key][i_rnn, :] for key in ['0', 'S2', 'G']], 0)

    i_plot_total = 0
    dict_keys = list(conv_dict.keys())[::-1]
    colour_dict_keys = {key: color_dict_stand[it] for it, key in enumerate(['S2', 'G', 'L1', 'dmc', '0', 'pred', 'pred_sep'])}
    colour_dict_keys['0'] = color_dict_stand[7]
    for key, val in colour_custom_dict.items():
        colour_dict_keys[key] = val
    linestyle_dict_keys = {x: '-' for x in label_dict_keys.keys()}
    for key, val in linestyle_custom_dict.items():
        linestyle_dict_keys[key] = val

    for key in dict_keys:
        mat = conv_dict[key]
        if normalise_start:
            mat = mat / np.mean(mat[:, 0])#[:, np.newaxis]
        plot_arr = np.mean(mat, 0)
        # if normalise_start:
        #     plot_arr = plot_arr / plot_arr[0]
        if plot_top:
            if (list_top is not None and key in list_top) or (list_top is None and '_' not in key and 'L' not in key):
                # print(key)
                # print(label_dict_keys.keys(), linestyle_dict_keys.keys(), colour_dict_keys.keys())
                ax_top.plot(plot_arr, label=label_dict_keys[key], linestyle=linestyle_dict_keys[key], linewidth=lw, color=colour_dict_keys[key])
                if plot_std:
                    ax_top.fill_between(x=np.arange(len(plot_arr)), y1=plot_arr - np.std(mat, 0),
                                        y2=plot_arr + np.std(mat, 0), alpha=0.2, color=colour_dict_keys[key])
                if plot_indiv:
                    for i_rnn in range(mat.shape[0]):
                        ax_top.plot(mat[i_rnn, :], label=None, linestyle=linestyle_dict_keys[key],
                                    linewidth=1, color=colour_dict_keys[key])

                i_plot_total += 1
        if plot_bottom:
            if key == 'L1':
                ax_bottom.plot(plot_arr, label=key, linestyle='-', linewidth=lw, color=colour_dict_keys[key])
                if plot_std:
                    ax_bottom.fill_between(x=np.arange(len(plot_arr)), y1=plot_arr - np.std(mat, 0),
                                        y2=plot_arr + np.std(mat, 0), alpha=0.2, color=colour_dict_keys[key])
                i_plot_total += 1
    if plot_top:
        ax_top.set_ylabel('Loss function ($H$)')
        ax_top.set_xlabel('Epoch'); #ax.set_ylabel('error relative')
        # ax_top.legend(frameon=False, bbox_to_anchor=(0.5, 0.2)); #ax.set_xlim([0, 10])
    if plot_bottom:
        ax_bottom.legend(frameon=False)
        ax_bottom.set_ylabel('L1 regularisation')
        ax_bottom.set_xlabel('Epoch'); #ax.set_ylabel('error relative')

    return (ax_top, ax_bottom)

def len_data_files(dir_path):
    return len([x for x in os.listdir(dir_path) if x[-5:] == '.data'])

def plot_split_perf_custom(folder_pred=None, folder_dmcpred=None, folder_dmc=None, ax=None,
                           plot_legend=True, legend_anchor=(1, 1), task_type='dmc',
                           plot_std=True, plot_indiv=False, plot_pred=True, plot_spec=True):
    if ax is None:
        ax = plt.subplot(111)

    ## prediction only
    if folder_pred is not None and os.path.exists(folder_pred) and plot_pred:
        _ = plot_split_perf(rnn_folder=folder_pred, list_top=['pred'], lw=5,
                            linestyle_custom_dict={'pred': '-'}, colour_custom_dict={'pred': pred_only_colour},
                            plot_std=plot_std, plot_indiv=plot_indiv,
                            ax_top=ax, ax_bottom=None, plot_bottom=False,
                            label_dict_keys={'pred': f'Cat STL' + f' ({len_data_files(folder_pred)} networks)'})
                            # label_dict_keys={'pred': 'H Pred' + f'    (Pred-only, N={len_data_files(folder_pred)})'})

    ## dmc only
    if folder_dmc is not None and os.path.exists(folder_dmc) and plot_spec:
        _ = plot_split_perf(rnn_folder=folder_dmc, list_top=[task_type], lw=5, plot_total=False,
                            linestyle_custom_dict={task_type: '-'}, colour_custom_dict={task_type: spec_only_colour},
                            plot_std=plot_std, plot_indiv=plot_indiv,
                            ax_top=ax, ax_bottom=None, plot_bottom=False,
                            label_dict_keys={task_type: f'Cat STL' + f' ({len_data_files(folder_dmc)} networks)'})
                            # label_dict_keys={task_type: f'H {task_type}' + f'   ({task_type}-only, N={len_data_files(folder_dmc)})'})

    ## dmc+ prediction only
    if folder_dmcpred is not None and os.path.exists(folder_dmcpred):
        list_top = []
        if plot_pred:
            list_top.append('pred')
        if plot_spec:
            list_top.append(task_type)

        _ = plot_split_perf(rnn_folder=folder_dmcpred, list_top=list_top, lw=5,
                            linestyle_custom_dict={'pred': '--', task_type: '-'},
                            colour_custom_dict={'pred': pred_spec_colour, task_type: pred_spec_colour},
                            plot_std=plot_std, plot_indiv=plot_indiv,
                            ax_top=ax, ax_bottom=None, plot_bottom=False,
                            label_dict_keys={'pred': f'Cat MTL' + f' ({len_data_files(folder_dmcpred)} networks)',
                                             task_type: f'Cat MTL' + f' ({len_data_files(folder_dmcpred)} networks)'})
                            # label_dict_keys={'pred': f'H Pred' + f'    (Pred & {task_type},  N={len_data_files(folder_dmcpred)})',
                            #                  task_type: f'H {task_type}' + f'   (Pred & {task_type},  N={len_data_files(folder_dmcpred)})'})

    if plot_legend:
        ax.legend(frameon=False)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    if plot_pred:
        ax.set_ylim([-0.05, 3.5])
    else:
        ax.set_ylim([-0.05, 1.5])
    return ax

def plot_n_nodes_convergence(parent_folder='/home/thijs/repos/rotation/models/sweep_n_nodes/7525/dmc_task/onehot/sparsity_5e-03/',
                   plot_legend=True, ax=None, plot_std=True, plot_indiv=False):
    list_child_folders = os.listdir(parent_folder)
    if ax is None:
        ax = plt.subplot(111)
    for i_f, cfolder in enumerate(list_child_folders):
        n_nodes = int(cfolder.split('_')[0])
        full_folder = os.path.join(parent_folder, cfolder, 'pred_only')
        _ = plot_split_perf(rnn_folder=full_folder, list_top=['pred'], lw=5,
                            linestyle_custom_dict={'pred': '-'}, colour_custom_dict={'pred': color_dict_stand[i_f]},
                            plot_std=plot_std, plot_indiv=plot_indiv,
                            ax_top=ax, ax_bottom=None, plot_bottom=False,
                            label_dict_keys={'pred': f'N_nodes={n_nodes} N={len_data_files(full_folder)})'})
    if plot_legend:
        ax.legend(frameon=False, bbox_to_anchor=(1, 1), loc='upper right')
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.set_ylim([-0.05, 1.05])

def plot_n_nodes_sweep(parent_folder='/home/thijs/repos/rotation/models/sweep_n_nodes/7525/dmc_task/onehot/sparsity_1e-03/',
                  verbose=0, ax=None, method='integral', color='k', print_labels=True):
    list_child_folders = os.listdir(parent_folder)
    if ax is None:
        ax = plt.subplot(111)
    learn_eff_dict = {}
    for i_f, cfolder in enumerate(list_child_folders):
        n_nodes = int(cfolder.split('_')[0])
        full_folder = os.path.join(parent_folder, cfolder, 'pred_only')
        tmp_dict = ru.compute_learning_index(rnn_folder=full_folder, list_loss=['pred'],
                                                   method=method)
        learn_eff_dict[n_nodes] = tmp_dict['pred']
    learn_eff_df = pd.DataFrame(learn_eff_dict)
    learn_eff_df = pd.melt(learn_eff_df, value_vars=[x for x in [5, 10, 15, 20, 25]])
    learn_eff_df.columns = ['n_nodes', 'learning_index']
    g = sns.pointplot(data=learn_eff_df, x='n_nodes', y='learning_index', ax=ax, color=color, alpha=0.7)
    plt.setp(g.collections, alpha=0.6)
    plt.setp(g.lines, alpha=0.6)
    if print_labels:
        ax.set_xlabel('Number of neurons')
        if method == 'integral':
            ax.set_ylabel('Speed of convergence\nof prediction task')
        elif method == 'final_loss':
            ax.set_ylabel('Final loss of\nprediction task')
        ax.set_title('Optimal network size\nfor various sparsity values', fontdict={'weight': 'bold'})
        ax = despine(ax)

def plot_n_nodes_sweep_multiple(super_folder='/home/thijs/repos/rotation/models/sweep_n_nodes/7525/dmc_task/onehot',
                                ax=None, method='integral'):
    if ax is None:
        ax = plt.subplot(111)
    spars_folders = os.listdir(super_folder)
    label_list = []
    for ii, spars_folder in enumerate(spars_folders):
        plot_n_nodes_sweep(parent_folder=os.path.join(super_folder, spars_folder), ax=ax,
                            method=method, print_labels=(ii == len(spars_folders) - 1),
                            color='#696969')
                            # color=color_dict_stand[ii])
        label_list.append(spars_folder.split('_')[1])
        # if ii == 5:
        #     break
    # ax.legend(label_list, frameon=False)
    if method == 'integral':
        ax.set_ylim([0.5, 1.05])

    ax.arrow(4.35, 0.75, 0, -0.1, head_width=0.3, head_length=0.03, linewidth=1,
              color='k', length_includes_head=True)
    ax.text(s='sparsity', x=4.55, y=0.63, rotation=90, fontsize=12)

def plot_late_s2_comparison(late_s2_folder='/home/thijs/repos/rotation/models/late_s2/7525/dmc_task/onehot/sparsity_1e-03/pred_only',
                            early_s2_folder='/home/thijs/repos/rotation/models/7525/dmc_task/onehot/sparsity_1e-03/pred_only',
                            method='integral', ax=None):
    if ax is None:
        ax = plt.subplot(111)
    learn_eff_dict = {}
    dict_early = ru.compute_learning_index(rnn_folder=early_s2_folder, list_loss=['pred'],
                                               method=method)
    learn_eff_dict['early'] = dict_early['pred']
    dict_late = ru.compute_learning_index(rnn_folder=late_s2_folder, list_loss=['pred'],
                                               method=method)
    learn_eff_dict['late'] = dict_late['pred']
    learn_eff_df = pd.DataFrame(learn_eff_dict)
    learn_eff_df = pd.melt(learn_eff_df, value_vars=['early', 'late'])
    learn_eff_df.columns = ['s2_timing', 'learning_index']
    sns.pointplot(data=learn_eff_df, x='s2_timing', y='learning_index', ax=ax, color='k', join=False)
    p_val = scipy.stats.wilcoxon(dict_early['pred'], dict_late['pred'],
                                       alternative='two-sided')[1]
    print(p_val, 'late s2')
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    ax.plot([0.2, 0.8], [0.627, 0.627], c='k')
    if p_val < 0.01:
        ax.text(s=f'P < 10^-{str(int(ru.two_digit_sci_not(p_val)[-2:]) - 1)}', x=0.2, y=0.63)
    else:
        ax.text(s=f'n.s.', x=0.4, y=0.68)
    ax.set_xlim(xlim)
    # ax.set_ylim(ylim)
    ax.set_ylim([-0.05, 1.6])
    ax.set_xlabel('Timing of stimulus 2')
    if method == 'integral':
        ax.set_ylabel('Speed of convergence of\nprediction task')
    elif method == 'final_loss':
        ax.set_ylabel('Final loss of\nprediction task')
    ax.set_title('Stimulus timing does not \ncause learning difference', fontdict={'weight': 'bold'})
    ax = despine(ax)
    ax.set_ylim()

def plot_stl_mtl_comparison(dmc_only_folder='/home/thijs/repos/rotation/models/7525/dmc_task/onehot/sparsity_1e-03/dmc_only/',
                            pred_dmc_folder='/home/thijs/repos/rotation/models/7525/dmc_task/onehot/sparsity_1e-03/pred_dmc/',
                            method='integral', ax=None):
    if ax is None:
        ax = plt.subplot(111)
    learn_eff_dict = {}
    dict_stl = ru.compute_learning_index(rnn_folder=dmc_only_folder, list_loss=['dmc'],
                                           method=method)
    learn_eff_dict['single'] = dict_stl['dmc']
    dict_mtl = ru.compute_learning_index(rnn_folder=pred_dmc_folder, list_loss=['dmc'],
                                               method=method)
    learn_eff_dict['dual'] = dict_mtl['dmc']
    learn_eff_df = pd.DataFrame(learn_eff_dict)
    learn_eff_df = pd.melt(learn_eff_df, value_vars=['single', 'dual'])
    learn_eff_df.columns = ['network_task', 'learning_index']
    sns.pointplot(data=learn_eff_df, x='network_task', y='learning_index', ax=ax, color='k', join=False)
    p_val = scipy.stats.wilcoxon(dict_stl['dmc'], dict_mtl['dmc'],
                                       alternative='two-sided')[1]
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    ax.plot([0.2, 0.8], [0.6, 0.6], c='k')
    if p_val < 0.01:
        if str(int(ru.two_digit_sci_not(p_val)[-2:]) - 1) == '4':
            ax.text(s='P < 10$^{-4}$', x=0.2, y=0.63)
        elif str(int(ru.two_digit_sci_not(p_val)[-2:]) - 1) == '3':
            ax.text(s='P < 10$^{-3}$', x=0.2, y=0.63)
        else:
            assert False, f'p value is {p_val}'
    else:
        ax.text(s=f'n.s.', x=0.4, y=0.63)
    ax.set_xlim(xlim)
    # ax.set_ylim(ylim)
    ax.set_ylim([-0.05, 1.6])
    print(p_val, 'mtl stl')
    ax.set_xlabel('Learning tasks')
    if method == 'integral':
        ax.set_ylabel('Speed of convergence of\ncategorisation task')
    elif method == 'final_loss':
        ax.set_ylabel('Final loss of\ncategorisation task')
    ax.set_title('Dual task networks eavesdrop\nto learn the categorisation task', fontdict={'weight': 'bold'})
    ax = despine(ax)

def plot_7525_5050_comparison(folder_50='/home/thijs/repos/rotation/models/5050/dmc_task/onehot/sparsity_1e-03/pred_dmc/',
                            folder_75='/home/thijs/repos/rotation/models/7525/dmc_task/onehot/sparsity_1e-03/pred_dmc/',
                            method='integral', ax=None):
    if ax is None:
        ax = plt.subplot(111)
    learn_eff_dict = {}
    dict_50 = ru.compute_learning_index(rnn_folder=folder_50, list_loss=['dmc'],
                                           method=method)
    learn_eff_dict['0.50'] = dict_50['dmc']
    dict_75 = ru.compute_learning_index(rnn_folder=folder_75, list_loss=['dmc'],
                                               method=method)
    learn_eff_dict['0.75'] = dict_75['dmc']
    learn_eff_df = pd.DataFrame(learn_eff_dict)
    learn_eff_df = pd.melt(learn_eff_df, value_vars=['0.50', '0.75'])
    learn_eff_df.columns = ['ratio_alpha_beta', 'learning_index']
    sns.pointplot(data=learn_eff_df, x='ratio_alpha_beta', y='learning_index',
                  ax=ax, color='k', join=False)
    p_val = scipy.stats.wilcoxon(dict_50['dmc'], dict_75['dmc'],
                                       alternative='two-sided')[1]
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    ax.plot([0.2, 0.8], [0.6, 0.6], c='k')
    if p_val < 0.01:
        if str(int(ru.two_digit_sci_not(p_val)[-2:]) - 1) == '4':
            ax.text(s='P < 10$^{-4}$', x=0.2, y=0.63)
        elif str(int(ru.two_digit_sci_not(p_val)[-2:]) - 1) == '3':
            ax.text(s='P < 10$^{-3}$', x=0.2, y=0.63)
        elif str(int(ru.two_digit_sci_not(p_val)[-2:]) - 1) == '2':
            ax.text(s='P < 10$^{-2}$', x=0.2, y=0.63)
        else:
            assert False
    else:
        ax.text(s=f'n.s.', x=0.4, y=0.63)
    ax.set_xlim(xlim)
    ax.set_ylim([-0.05, 1.6])
    print(p_val, 'mtl stl')
    # ax.set_xlabel('Ratio ' + r"$\alpha$" + '/' + r"$\beta$")
    ax.set_xlabel(r'$P(\alpha = \beta)$')
    if method == 'integral':
        ax.set_ylabel('Speed of convergence of\ncategorisation task')
    elif method == 'final_loss':
        ax.set_ylabel('Final loss of\ncategorisation task')
    ax.set_title('Correlated stimuli are required\nfor eavesdropping', fontdict={'weight': 'bold'})
    ax = despine(ax)

def plot_example_trial(trial, ax=None, yticklabels=output_vector_labels,
                       xticklabels=time_labels_blank[1:], c_bar=True,
                       vmin=None, vmax=None, c_map='magma', print_labels=True):
    '''Plot 1 example trial'''
    if ax is None:
        ax = plt.subplot(111)

    sns.heatmap(trial.T, yticklabels=yticklabels, cmap=c_map, cbar=c_bar,
            xticklabels=xticklabels, ax=ax, vmin=vmin, vmax=vmax, )
    bottom, top = ax.get_ylim()
    ax.set_ylim(bottom + 0.5, top - 0.5)
    ax.set_yticklabels(labels=yticklabels, rotation=0)
    ax.set_xticklabels(labels=xticklabels, rotation=0)
    if print_labels:
        ax.set_xlabel('Time')
        ax.set_ylabel('Stimulus vector')
    return ax

def plot_effect_eavesdropping_learning(task='dmc', ratio_exp_str='7525', nature_stim='onehot',
                                       sparsity_str='1e-03', ax=None, plot_legend=True, verbose=0,
                                       plot_std=True, plot_indiv=False, plot_pred=True, plot_spec=True):
   base_folder = f'models/{ratio_exp_str}/{task}_task/{nature_stim}/sparsity_{sparsity_str}/'
   # print('USING SAVED STATE')
   folders_dict = {}
   folders_dict['pred_only'] = base_folder + 'pred_only/'
   folders_dict[f'{task}_only'] = base_folder + f'{task}_only/'
   folders_dict[f'pred_{task}'] = base_folder + f'pred_{task}/'
   # print(folders_dict)
   plot_split_perf_custom(folder_pred=folders_dict['pred_only'],
                          folder_dmc=folders_dict[f'{task}_only'],
                          folder_dmcpred=folders_dict[f'pred_{task}'],
                          plot_std=plot_std, plot_indiv=plot_indiv,
                          task_type=task, ax=ax, plot_legend=plot_legend,
                          plot_pred=plot_pred, plot_spec=plot_spec)
   plt.title(task + r'$\; P(\alpha = \beta) = $' + f'0.{ratio_exp_str[:2]},' + r'$ \; \; \lambda=$' + f'{sparsity_str}');

   if verbose > 0:

       for key, folder_rnns in folders_dict.items():
           if os.path.exists(folder_rnns):
               list_keys = key.split('_')
               if 'only' in list_keys:
                   list_keys.remove('only')
               learn_eff = ru.compute_learning_index(rnn_folder=folder_rnns,
                                                     list_loss=list_keys)
               print(key, {x: (np.round(np.mean(learn_eff[x]), 4), np.round(np.std(learn_eff[x]), 4)) for x in list_keys})

def plot_learning_efficiency(task_list=['dms', 'dmc'], plot_difference=False, indicate_sparsity=False,
                             method='integral', nature_stim_list=['periodic', 'onehot'], ax=None):
    df = ru.calculate_all_learning_eff_indices(method=method, task_list=task_list,
                                                nature_stim_list=nature_stim_list)
    # assert len(task_list) == 2
    if ax is None:
        fig, ax = plt.subplots(1, len(nature_stim_list), figsize=(6 * len(nature_stim_list), 3), gridspec_kw={'wspace': 0.7})
    if len(nature_stim_list) == 1:
        ax = [ax]
    i_plot = 0
    if plot_difference:
        tmp_df = df[[x[:4] != 'pred' for x in df['loss_comp']]].groupby(['task', 'nature_stim', 'setting','sparsity']).mean()  # compute mean for each set of conditions [ across simulations]
        multi_rows = [True if x[2] == 'multi' else False for x in tmp_df.index]  # select multitask settings
        tmp_df['learning_eff'][multi_rows] *= -1   # multiple effiency with -1 so the difference can be computed using condition-specific sum
        tmp_df = tmp_df.groupby(['task', 'nature_stim', 'sparsity']).sum()  # effectively comppute difference
        tmp_df.reset_index(inplace=True)  # bring multi indexes back to column values
        for i_nat, nat in enumerate(nature_stim_list):
            g = sns.lineplot(data=tmp_df[tmp_df['nature_stim'] == nat], x='sparsity', y='learning_eff',
                         style='task', ax=ax[i_plot], color='k', linewidth=4, markers=True)
            # ax[i_plot].plot([0, 0.2], [0, 0], c='grey')
            # plt.setp(g.collections, sizes=[65])

            # ax[i_plot].set_ylabel(f'Eavesdropping effect\n(difference in {method})')
            i_plot += 1
    else:
        spec_task_df = df[[x.split('_')[0] in task_list for x in df['loss_comp']]]
        for i_nat, nat in enumerate(nature_stim_list):
            g = sns.lineplot(data=spec_task_df[spec_task_df['nature_stim'] == nat], x='sparsity', y='learning_eff',
                         hue='setting', style='task', markers=True, ci=95, linewidth=1.5,
                         ax=ax[i_plot], hue_order=['multi', 'single'])
            # ax[i_plot].set_ylim([0, 1.1])
            plt.setp(g.collections, alpha=0.1)
            plt.setp(g.lines, alpha=0.6)

            # ax[i_plot].set_ylabel('Learning efficiency index\n(= integral loss function)')
            i_plot += 1
    for i_plot in range(len(ax)):
        # ax[i_plot].set_xscale('log', nonposx='clip')
        ax[i_plot].set_xscale('symlog', linthreshx=2e-6)
        if len(nature_stim_list) > 1:
            ax[i_plot].legend(bbox_to_anchor=(1.4, 1), loc='upper right')
            ax[i_plot].set_title(nature_stim_list[i_plot], fontdict={'weight': 'bold'})
        else:
            ax[i_plot].set_title('Eavesdropping is sparsity dependent', fontdict={'weight': 'bold'})
            ax[i_plot].get_legend().remove()
        ax[i_plot].set_xlabel('Sparsity regularisation')
        if method == 'final_loss':
            ax[i_plot].set_ylim([-0.02, 1.2])
        elif method == 'integral':
            ax[i_plot].set_ylim([-0.02, 1.5])
        if indicate_sparsity:

            ax[i_plot].arrow(0.015, -0.32, 0.05,0, head_width=0.07, head_length=0.02, linewidth=1,
                      color='k', length_includes_head=True, clip_on=False)
            ax[i_plot].text(s='sparser', x=0.014, y=-0.45, fontsize=12)

        despine(ax[i_plot])

        if method == 'integral':
            ax[i_plot].set_ylabel('Speed of convergence of\ncategorisation task')
        elif method == 'final_loss':
            ax[i_plot].set_ylabel('Final loss of\ncategorisation task')

    return df

def plot_sa_convergence(sa_folder_list=['/home/thijs/repos/rotation/models/simulated_annealing/7525/dmc_task/onehot/sparsity_1e-03/pred_dmc'],
                        figsize=None, plot_std=True, plot_indiv=False):
    if figsize is None:
        figsize = (6 * len(sa_folder_list), 3)
    fig = plt.figure(constrained_layout=False, figsize=figsize)
    gs_conv = fig.add_gridspec(ncols=len(sa_folder_list), nrows=1, bottom=0, top=0.75, left=0, right=1, wspace=0.3)
    gs_ratio = fig.add_gridspec(ncols=len(sa_folder_list), nrows=1, bottom=0.85, top=1, left=0, right=1, wspace=0.3)

    ax_conv, ax_ratio, ratio_exp_array = {}, {}, {}
    letters = ['A', 'B', 'C', 'D']
    for i_col, sa_folder in enumerate(sa_folder_list):

        ax_conv[i_col] = fig.add_subplot(gs_conv[i_col])
        ax_ratio[i_col] = fig.add_subplot(gs_ratio[i_col])

        for i_rnn, rnn_name in enumerate(os.listdir(sa_folder)):
            rnn = ru.load_rnn(os.path.join(sa_folder, rnn_name))
            assert rnn.info_dict['simulated_annealing']
            if i_rnn == 0:
                ratio_exp_array[i_col] = rnn.info_dict['ratio_exp_array']
            else:
                assert (ratio_exp_array[i_col] == rnn.info_dict['ratio_exp_array']).all()


        plot_split_perf_custom(folder_pred=None,
                               folder_dmc=None,
                               folder_dmcpred=sa_folder,
                               plot_std=plot_std, plot_indiv=plot_indiv,
                               task_type='dmc', ax=ax_conv[i_col], plot_legend=False,
                               plot_pred=False, plot_spec=True)
        ax_ratio[i_col].plot(ratio_exp_array[i_col], linewidth=3, c='grey')
        ax_ratio[i_col].set_xticklabels([])
        ax_ratio[i_col].set_ylim([0.45, 0.85])
        despine(ax_ratio[i_col])
        ax_ratio[i_col].text(s=letters[i_col], x=-40, y=1.2, fontdict={'weight': 'bold'})
        ax_ratio[i_col].set_ylabel(r'$P(\alpha = \beta)$');
        fig.align_ylabels(axs=[ax_ratio[i_col], ax_conv[i_col]])
    ax_ratio[0].set_title('Simulated annealing of stimulus correlation ' + r'$P(\alpha = \beta)$' + '\nenables RNNs to learn the categorisation task with ' + r'$P(\alpha = \beta) = 0.5$',
                            fontdict={'weight': 'bold'})
    if len(sa_folder_list) == 2:
        ax_ratio[1].set_title('Whereas tasks with a constant ' + r'$P(\alpha = \beta) = 0.5$' + ' do not learn\nto solve the task',
                                fontdict={'weight': 'bold'})
    return fig

def plot_autotemp_s1_decoding(parent_folder='/home/thijs/repos/rotation/models/7525/dmc_task/onehot/sparsity_1e-03/',
                              ax=None, plot_legend=False):

    if ax is None:
        ax = plt.subplot(111)

    child_folders = os.listdir(parent_folder)

    for cf in child_folders:
        rnn_folder = os.path.join(parent_folder, cf + '/')
        bpm.train_multiple_decoders(rnn_folder=rnn_folder, ratio_expected=0.5,
                                    n_samples=None, ratio_train=0.8, label='s1',
                                    reset_decoders=True, skip_if_already_decoded=True)  # check if decoding has been done before
    autotemp_dec_dict = {}
    n_tp = 13  # for t_stim = 2 and t_dleay = 2
    colour_dict = {'pred_only': pred_only_colour, 'dmc_only': spec_only_colour,
                  'pred_dmc': pred_spec_colour}
    for cf in child_folders:
        rnn_folder = os.path.join(parent_folder, cf + '/')
        list_rnns = os.listdir(rnn_folder)
        autotemp_dec_dict[cf] = np.zeros((len(list_rnns), n_tp))
        for i_rnn, rnn_name in enumerate(list_rnns):
            rnn = ru.load_rnn(os.path.join(rnn_folder, rnn_name))
            autotemp_score = rnn.decoding_crosstemp_score['s1'].diagonal()
            autotemp_dec_dict[cf][i_rnn, :] = autotemp_score
        mean_dec = autotemp_dec_dict[cf].mean(0)
        std_dec = autotemp_dec_dict[cf].std(0)
        ax.plot(mean_dec, linewidth=3, label=cf, c=colour_dict[cf])
        ax.fill_between(x=np.arange(n_tp), y1=mean_dec - std_dec, y2=mean_dec + std_dec, alpha=0.3, facecolor=colour_dict[cf])
    if plot_legend:
        ax.legend()
    ax.set_xticks(np.arange(n_tp))
    ax.set_xticklabels(time_labels_blank[:-1])
    ax.set_ylim([0.45, 1.05])
    ax.set_xlabel('Time')
    ax.set_ylabel('S1 decoding accuracy')
    ax.set_title('S1 memory')
    despine(ax)


def plot_autotemp_all_reps_decoding(rnn_folder='/home/thijs/repos/rotation/models/7525/dms_task/onehot/sparsity_1e-04/pred_dms/',
                              ax=None, plot_legend=True, reset_decoders=True, skip_if_already_decoded=False):

    if ax is None:
        ax = plt.subplot(111)


    for i_rep, rep in enumerate(['s1', 's2', 'go']):
        print(rep)
        if reset_decoders:
            res = (i_rep == 0)
        else:
            res = False
        bpm.train_multiple_decoders(rnn_folder=rnn_folder, ratio_expected=0.5,
                                    n_samples=None, ratio_train=0.8, label=rep,
                                    reset_decoders=res, skip_if_already_decoded=skip_if_already_decoded)  # check if decoding has been done before
    autotemp_dec_dict = {}
    n_tp = 13  # for t_stim = 2 and t_dleay = 2
    colour_dict = {'s1': pred_spec_colour, 's2': pred_spec_colour,
                  'go': pred_spec_colour}
    linestyle_dict = {'s1': '-', 's2': '--', 'go': ':'}

    for i_rep, rep in enumerate(['s1', 's2', 'go']):
        list_rnns = os.listdir(rnn_folder)
        autotemp_dec_dict[rep] = np.zeros((len(list_rnns), n_tp))
        for i_rnn, rnn_name in enumerate(list_rnns):
            rnn = ru.load_rnn(os.path.join(rnn_folder, rnn_name))
            autotemp_score = rnn.decoding_crosstemp_score[rep].diagonal()
            autotemp_dec_dict[rep][i_rnn, :] = autotemp_score
        mean_dec = autotemp_dec_dict[rep].mean(0)
        std_dec = autotemp_dec_dict[rep].std(0)
        ax.plot(mean_dec, linewidth=3, label=rep, c=colour_dict[rep], linestyle=linestyle_dict[rep])
        ax.fill_between(x=np.arange(n_tp), y1=mean_dec - std_dec, y2=mean_dec + std_dec,
                        alpha=0.3, facecolor=colour_dict[rep])
    if plot_legend:
        ax.legend()
    ax.set_xticks(np.arange(n_tp))
    ax.set_xticklabels(time_labels_blank[:-1])
    ax.set_ylim([0.45, 1.05])
    ax.set_xlabel('Time')
    ax.set_ylabel('Decoding accuracy')
    ax.set_title('Memory of S1, S2 and M/NM')
    despine(ax)

def plot_correlation_matrix(rnn, representation='s1', ax=None, hard_reset=False):
    if ax is None:
        ax = plt.subplot(111)

    if hard_reset:
        bpm.save_pearson_corr(rnn=rnn, representation=representation)
    else:
        ru.ensure_corr_mat_exists(rnn=rnn, representation=representation)

    sns.heatmap(copy.deepcopy(rnn.rep_corr_mat_dict[representation]), cmap='BrBG',
                ax=ax, xticklabels=time_labels_blank[:-1], yticklabels=time_labels_blank[:-1],
                cbar='BrBG', vmin=-1, vmax=1)
    ax.set_yticklabels(rotation=90, labels=ax.get_yticklabels())
    ax.set_ylabel('Time')
    ax.set_xlabel('Time');
    ax.invert_yaxis()
    bottom, top = ax.get_ylim()
    ax.set_ylim(bottom - 0.5, top + 1.5)

def plot_decoding_matrix(rnn, representation='s1', ax=None):
    if ax is None:
        ax = plt.subplot(111)

    score_mat, _, __ = bpm.train_single_decoder_new_data(rnn=rnn, save_inplace=False,
                                            label=representation)          ## calculate autotemp score

    sns.heatmap(copy.deepcopy(score_mat), cmap='BrBG',
                ax=ax, xticklabels=time_labels_blank[:-1], yticklabels=time_labels_blank[:-1],
                cbar='BrBG', vmin=0, vmax=1)
    ax.set_yticklabels(rotation=90, labels=ax.get_yticklabels())
    ax.set_ylabel('Time')
    ax.set_xlabel('Time');
    ax.invert_yaxis()
    bottom, top = ax.get_ylim()
    ax.set_ylim(bottom - 0.5, top + 1.5)

def plot_hist_rot_indices(rnn_folder, representation='s1', ax=None):
    if ax is None:
        ax = plt.subplot(111)

    list_rnns = [x for x in os.listdir(rnn_folder) if x[-5:] == '.data']
    rot_ind_arr = np.zeros(len(list_rnns))
    for i_rnn, rnn_name in enumerate(list_rnns):
        rnn = ru.load_rnn(os.path.join(rnn_folder, rnn_name))
        ru.ensure_corr_mat_exists(rnn=rnn, representation=representation)
        corr_mat = rnn.rep_corr_mat_dict[representation]
        corr_s1s2_block = corr_mat[np.array([2, 3]), :][:, np.array([6, 7])]
        assert corr_s1s2_block.shape == (2, 2)
        rot_ind_arr[i_rnn] = np.mean(corr_s1s2_block)
        if rnn.info_dict['task'] == 'pred_dmc':
            print(rot_ind_arr[i_rnn], np.mean(rnn.test_loss_split['dmc'][-10:]))
    ax.hist(rot_ind_arr, bins=np.linspace(-1, 1, 21), histtype='step', linewidth=3)

def plot_autotemp_s1_different_epochs(rnn_name='/home/thijs/repos/rotation/models/save_state/7525/dmc_task/onehot/sparsity_1e-03/pred_dmc/rnn-mnm_2021-05-13-2134.data',
                                      epoch_list=[1, 2, 4, 6, 8, 10, 12, 15, 18, 20, 25, 40],
                                      ax=None, autotemp_dec_dict=None, plot_legend=True):
    if ax is None:
        ax = plt.subplot(111)
    n_tp = 13
    rnn = ru.load_rnn(rnn_name)
    autotemp_dec_dict = ru.calculate_autotemp_different_epochs(rnn=rnn, epoch_list=epoch_list,
                                                              autotemp_dec_dict=autotemp_dec_dict)

    alpha_list = [0.88 ** ii for ii in range(len(epoch_list))]
    for i_epoch, epoch in tqdm(enumerate(epoch_list)):
        ax.plot(autotemp_dec_dict[epoch], linewidth=3, color=pred_spec_colour, #'#000087',
                alpha=alpha_list[::-1][i_epoch], label=f'epoch {epoch}')

    ax.set_xticks(np.arange(n_tp))
    ax.set_xticklabels(time_labels_blank[:-1])
    ax.set_xlabel('Time')
    ax.set_ylim([0.45, 1.05])
    ax.set_ylabel('S1 decoding accuracy ')
    despine(ax)
    if plot_legend:
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), frameon=False)
    ax.set_title('S1 memory over epochs')

    return autotemp_dec_dict


def plot_raster_trial_average(plot_diff, ax=None, reverse_order=False,
                              c_bar=True, ol=None, th=None,
                              index_label=0, representation='s1'):
    if representation == 'go':
        plot_cmap = 'RdGy'
    elif representation == 's1' or representation == 's2':
        plot_cmap = 'PiYG'
    if ax is None:
        ax = plt.subplot(111)
    assert plot_diff.shape == (20, 13)
    if ol is None:
        ol = opt_leaf(plot_diff, dim=0)  # optimal leaf sorting
        if reverse_order:
            ol = ol[::-1]
    # rev_ol = np.zeros_like(ol) # make reverse mapping of OL
    # for i_ol, el_ol in enumerate(ol):
    #     rev_ol[el_ol] = i_ol
    plot_diff = plot_diff[ol, :]
    if th is None:
        th = np.max(np.abs(plot_diff)) # threshold for visualisation

    sns.heatmap(plot_diff, cmap=plot_cmap, vmin=-1 * th, vmax=th, ax=ax,
                    xticklabels=time_labels_blank[:-1], cbar=c_bar)
    ax.set_yticklabels(rotation=0, labels=ax.get_yticklabels())
    ax.set_ylabel('neuron #')
    ax.invert_yaxis()
    ax.set_xticklabels(rotation=0, labels=ax.get_xticklabels())
    bottom, top = ax.get_ylim()
    ax.set_ylim(bottom - 0.5, top + 1.5)
    ax.set_title(f'Activity difference dependent on {representation}', weight='bold')
    ax.set_xlabel('Time');

    return ol
