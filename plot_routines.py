# @Author: Thijs van der Plas <TL>
# @Date:   2020-05-15
# @Email:  thijs.vanderplas@dtc.ox.ac.uk
# @Filename: plot_routines.py
# @Last modified by:   thijs
# @Last modified time: 2020-05-21



import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as patches
from mpl_toolkits.axes_grid1 import make_axes_locatable
from mpl_toolkits.axes_grid1.colorbar import colorbar as mpl_colorbar
import seaborn as sns
import pickle
import scipy.cluster, scipy.spatial
import bptt_rnn as bp
import rot_utilities as ru

## Some labels needed by a lot of funtions:
single_time_labels = ['0', 'A', '0', 'B', '0', 'C', '0', 'D', '0']
double_time_labels = []
double_time_labels_half = []
for stl in single_time_labels:
    double_time_labels.append(stl)
    double_time_labels.append(stl)
    double_time_labels_half.append(stl)
    double_time_labels_half.append('')
double_time_labels_blank = [x.replace('0', '') for x in double_time_labels]
single_time_labels_blank = [x.replace('0', '') for x in single_time_labels]
assert len(double_time_labels_half) == len(double_time_labels)
freq_labels = ['0', 'A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'D']
freq_labels_sub = [r"$0$", r"$A_1$", r"$A_2$", r"$B_1$", r"$B_2$", r"$C_1$", r"$C_2$", r"$D$"]

def plot_weights(rnn_layer, ax=None, title='weights', xlabel='',
                 ylabel='', xticklabels=None, yticklabels=None,
                 weight_order=None):
    '''Plot a weight matrix; given a RNN layer, with zero-symmetric clipping.'''
    if ax is None:
        ax = plt.subplot(111)
    weights = [x for x in rnn_layer.parameters()][0].detach().numpy()
    if weight_order is not None and weights.shape[0] == len(weight_order):
        weights = weights[weight_order, :]
    if weight_order is not None and weights.shape[1] == len(weight_order):
        weights = weights[:, weight_order]
    cutoff = np.percentile(np.abs(weights), 95)
    sns.heatmap(weights, ax=ax, cmap='PiYG', vmax=cutoff, vmin=-1 * cutoff)
    bottom, top = ax.get_ylim()
    ax.set_ylim(bottom + 0.5, top - 0.5)
    ax.set_title(title, weight='bold');
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
    if xticklabels is not None:
        ax.set_xticklabels(xticklabels)
    if yticklabels is not None:
        ax.set_yticklabels(yticklabels)
    return ax

def plot_all_UWV(rnn_model, freq_labels='', weight_order=None):
    '''Plot the 3 weight matrices  U, W and V.'''
    fig, ax_w = plt.subplots(1, 3)
    plot_weights(ax=ax_w[0], rnn_layer=rnn_model.lin_input,
                title='U - Input stimulus-neuron weights',
                xticklabels=freq_labels, ylabel='Neuron',
                weight_order=weight_order, xlabel='Input')


    plot_weights(ax=ax_w[1], rnn_layer=rnn_model.lin_feedback,
                 title='W - Feedback neuron-neuron weights',
                 ylabel='Neuron', xlabel='Neuron',
                 weight_order=weight_order)

    plot_weights(ax=ax_w[2], rnn_layer=rnn_model.lin_output,
                 title='V - Ouput neuron-prediction weights',
                 yticklabels=freq_labels, xlabel='Neuron',
                 ylabel='Output', weight_order=weight_order)
    return (fig, ax_w)

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

def plot_train_test_perf(rnn_model, ax=None, train=True, test=True):
    '''Plot train and test loss as function of epoch.'''
    if ax is None:
        ax = plt.subplot(111)
    if train:
        ax.plot(rnn_model.train_loss_arr, label='train', linewidth=3, color='k', linestyle=':')
    if test:
        ax.plot(rnn_model.test_loss_arr, label='test', linewidth=3, color='k')
    ax.set_xlabel('Epoch'); ax.set_ylabel("Loss");
    if train and test:
        ax.legend();
    return ax

def plot_decoder_crosstemp_perf(score_matrix, ax=None, ticklabels='', cmap_hm = 'BrBG', v_max=None, c_bar=True,
                                save_fig=False, fig_name='figures/example_low_crosstempmat.pdf'):
    '''Plot matrix of cross temporal scores for decoding'''
    if ax is None:
        ax = plt.subplot(111)
    # cmap_hm = sns.diverging_palette(145, 280, s=85, l=25, n=20)

    # cmap_hm = 'Greys'
    hm = sns.heatmap(score_matrix, cmap=cmap_hm, xticklabels=ticklabels, cbar=c_bar,
                           yticklabels=ticklabels, ax=ax, vmin=0, vmax=v_max,
                           linewidths=0.1, linecolor='k')
    bottom, top = ax.get_ylim()
    ax.set_ylim(bottom + 0.5, top - 0.5)
    ax.set_ylabel('Training time ' + r"$\tau$"); ax.set_xlabel('Testing time t')
    ax.set_title('Cross-temporal decoding score\nCorrelated single example', weight='bold');
    if save_fig:
        plt.savefig(fig_name, bbox_inches='tight')
    return (ax, hm)

def plot_raster_trial_average(forw, ax=None, save_fig=False, reverse_order=False, c_bar=True,
                              fig_name='figures/example_high_forward_difference.pdf'):
    labels_use_1 = np.array([x[0] == '1' for x in forw['labels_train']])
    labels_use_2 = np.array([x[0] == '2' for x in forw['labels_train']])
    if ax is None:
        ax = plt.subplot(111)

    plot_diff = (forw['train'][labels_use_1, :, :].mean(0) - forw['train'][labels_use_2, :, :].mean(0))
    ol = opt_leaf(plot_diff, dim=1)  # optimal leaf sorting
    if reverse_order:
        ol = ol[::-1]
    # ol = np.argsort(plot_diff.sum(0))
    # rev_ol = np.zeros_like(ol) # make reverse mapping of OL
    # for i_ol, el_ol in enumerate(ol):
    #     rev_ol[el_ol] = i_ol
    plot_diff = plot_diff[:, ol]
    th = np.max(np.abs(plot_diff)) # threshold for visualisation
    sns.heatmap(plot_diff.T, cmap='PiYG', vmin=-1 * th, vmax=th, ax=ax,
                     xticklabels=double_time_labels_blank[:-1], cbar=c_bar)
    bottom, top = ax.get_ylim()
    ax.set_ylim(bottom + 1.5, top - 0.5)
    ax.set_title('Activity difference between green and purple trials', weight='bold')
    ax.set_xlabel('Time'); ax.set_ylabel('neuron id');
    if save_fig:
        plt.savefig(fig_name, bbox_inches='tight')
    return ol

def plot_dynamic_decoding_axes(rnn, ticklabels=double_time_labels_blank[:-1],
                               neuron_order=None, label='alpha'):
    '''Plot the decoding axis w for each time point; and the diagonal auto-decoding
    accuracy on top. Returns these two axes. '''
    # if ax is None:
    #     ax = plt.subplot(111)

    decoder_axes = np.zeros((rnn.decoder_dict[label][0].coef_.size, len(rnn.decoder_dict[label])))
    for k, v in rnn.decoder_dict[label].items():
        decoder_axes[:, k] = v.coef_
    cutoff_w = np.percentile(np.abs(decoder_axes), 99)
    if neuron_order is not None:
        assert len(neuron_order) == decoder_axes.shape[0]
        decoder_axes = decoder_axes[neuron_order, :]

    ax_dec_diag = plt.subplot(3, 1, 1)
    ax_dec_diag.plot(np.diag(rnn.decoding_crosstemp_score[label]), linewidth=3,
                             linestyle='-', marker='.', markersize=10, color='k', alpha=0.6)
    ax_dec_diag.set_ylabel('Score')
    ax_dec_diag.set_title('Decoding performance (t = tau)')
    ax_dec_diag.set_xticks(np.arange(len(np.diag(rnn.decoding_crosstemp_score[label]))));
    ax_dec_diag.set_xticklabels(ticklabels);
    ax_dec_diag.set_xlim([-0.5, len(np.diag(rnn.decoding_crosstemp_score[label])) - 0.5])

    plt.subplot(3, 1, (2, 3))
    ax_dec_w = sns.heatmap(decoder_axes, xticklabels=ticklabels,
                          vmin=-1 * cutoff_w, vmax=cutoff_w, cmap='PiYG_r', cbar=False)
    bottom, top = ax_dec_w.get_ylim()
    ax_dec_w.set_ylim(bottom + 0.5, top - 0.5)
    ax_dec_w.set_xlabel('Time t'); ax_dec_w.set_ylabel('Neuron');
    return ax_dec_diag, ax_dec_w

def plot_example_trial(trial, ax=None, yticklabels=freq_labels_sub,
                       xticklabels=double_time_labels_blank[1:], c_bar=True,
                       vmin=0, vmax=1, c_map='magma', print_labels=True):
    '''Plot 1 example trial'''
    if ax is None:
        ax = plt.subplot(111)

    sns.heatmap(trial.T, yticklabels=yticklabels, cmap=c_map, cbar=c_bar,
            xticklabels=xticklabels, ax=ax, vmin=vmin, vmax=vmax)
    bottom, top = ax.get_ylim()
    ax.set_ylim(bottom + 0.5, top - 0.5)
    ax.set_yticklabels(labels=yticklabels, rotation=0)
    ax.set_xticklabels(labels=xticklabels, rotation=0)
    if print_labels:
        ax.set_xlabel('Time')
        ax.set_ylabel('Stimulus vector')
    return ax

def plot_time_trace_1_decoding_neuron(rnn, n_neuron=3, ax=None, label='alpha'):
    if ax is None:
        ax = plt.subplot(111)
    n_tp = len(rnn.decoder_dict[label])
    time_trace_pos = np.zeros(n_tp)
    time_trace_neg = np.zeros(n_tp)
    for i_tp in range(n_tp):
        time_trace_pos[i_tp] = np.clip(rnn.decoder_dict[label][i_tp].coef_[0][n_neuron], a_min=0, a_max=np.inf)
        time_trace_neg[i_tp] = -1 * np.clip(rnn.decoder_dict[label][i_tp].coef_[0][n_neuron], a_max=0, a_min=-1 * np.inf)
    ax.plot(time_trace_pos, linewidth=3, c='green')
    ax.plot(time_trace_neg, linewidth=3, c='m')
    ax.set_xlabel('time'); ax.set_ylabel('Decoding strenght')
    return ax

def plot_summary_ratios(agg_weights, agg_decoder_mat, agg_score,
                        time_labels=double_time_labels_blank[:-1], input_labels=freq_labels,
                        save_fig=False, fig_name='figures/details_ratio_exp_all.pdf'):
    '''Plot 3 subplots that summarise the differences between expected/Unexpected ratios
    1) average input weights; 2) average decoding weights; 3) dynamic decoding performance'''
    alpha_dict = {x: 0.2 + 0.2 * i_kk for i_kk, x in enumerate(agg_weights.keys())}  # transparency values
    list_ratios = list(agg_weights.keys()) #[75]
    ax_abs_w = plt.subplot(131)  # plot input weights
    for i_kk, kk in enumerate(list_ratios):
        ax_abs_w.plot(np.mean(agg_weights[kk], 0), alpha=alpha_dict[kk], color='k',
                      marker='.', linewidth=3, markersize=10, label=kk)
    #     ax_abs_w.bar(x=freq_labels, height=np.mean(agg_weights[kk], 0))
    plt.legend(); ax_abs_w.set_xticks(np.arange(agg_weights[kk].shape[1]));
    ax_abs_w.set_xticklabels(input_labels); ax_abs_w.set_ylabel('Average absolute weights')
    ax_abs_w.set_title('Average U input weight values', weight='bold')
    ax_abs_w.set_xlabel('Input node')

    ax_dec_w = plt.subplot(132)  # decoding weights
    for i_kk, kk in enumerate(list_ratios):
        ax_dec_w.plot(np.abs(agg_decoder_mat[kk]).mean((0, 1)), alpha=alpha_dict[kk], color='k',
                      marker='.', linewidth=3, markersize=10, label=kk)
    ax_dec_w.set_xticks(np.arange(agg_decoder_mat[75].shape[2]))
    ax_dec_w.set_xticklabels(time_labels);
    ax_dec_w.set_xlabel('Time'); ax_dec_w.set_ylabel('Average absolute weight');
    ax_dec_w.set_title('Average decoding weight values', weight='bold')

    ax_dec_perf = plt.subplot(133)  # decoding performance
    for i_kk, kk in enumerate(list_ratios):
        ax_dec_perf.plot(np.diag(agg_score[kk].mean(0)), alpha=alpha_dict[kk], color='k',
                      marker='.', linewidth=3, markersize=10, label=kk)
    ax_dec_perf.set_xticks(np.arange(agg_decoder_mat[75].shape[2]))
    ax_dec_perf.set_xticklabels(time_labels);
    ax_dec_perf.set_xlabel('Time'); ax_dec_w.set_ylabel('Accuracy');
    ax_dec_perf.set_title(r'$\alpha$ decoding performance', weight='bold', fontsize=15);
    ax_dec_perf.axvspan(xmin=10, xmax=17, alpha=0.15)
    ax_dec_perf.set_xlim([0, 17])
    # ax_abs_w.text(s='A', x=-2, y=0.22, fontdict={'fontsize': 20, 'weight':'bold'})
    # ax_abs_w.text(s='B', x=8.5, y=0.22, fontdict={'fontsize': 20, 'weight':'bold'})
    # ax_abs_w.text(s='C', x=19.5, y=0.22, fontdict={'fontsize': 20, 'weight':'bold'})
    if save_fig:
        plt.savefig(fig_name, bbox_inches='tight')

    return (ax_abs_w, ax_dec_w, ax_dec_perf)

def plot_alpha_beta_performance(alpha_perf, beta_perf, ax=None,
                                time_labels=double_time_labels_blank[:-1],
                                save_fig=False, fig_name='figures/alpha_beta_decoding_75.pdf'):
    '''Plot two lines - alpha_perf & beta_perf'''
    if ax is None:
        ax = plt.subplot(111)
    ax.plot(alpha_perf, alpha=0.9, color='#018571',
                  marker='', linewidth=3, markersize=18, label=r"$\alpha$")
    ax.plot(beta_perf, alpha=0.9, color='k', linestyle=':',
                  marker='', linewidth=3, markersize=18, label=r'$\beta$')
    ax.set_xticks(np.arange(len(time_labels)))
    ax.set_xticklabels(time_labels);
    ax.set_yticks([0.5, 0.75, 1])
    ax.set_xlabel('Time ' + r'$\to$'); ax.set_ylabel('Accuracy');
    # ax.legend(bbox_to_anchor=(1,0 , 0, 1), fontsize=20)
    ax.legend(bbox_to_anchor=(0.85, 0.1, 0, 1))
    # ax.set_title(r'$\alpha$ decoding performance', weight='bold', fontsize=15);
    # ax.axvspan(xmin=10, xmax=17, alpha=0.15)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_xlim([0, 17]);
    if save_fig:
        plt.savefig(fig_name, bbox_inches='tight')
    return ax

def plot_stable_switch_bar_diagram(stable_list, switch_list, ax=None, bar_width=0.35,
                                   save_fig=False, fig_name='figures/stable_switch_correlated.pdf'):
    '''Plot bar diagram of number of stable & switch neurons '''
    assert len(stable_list) == len(switch_list)
    if ax is None:
        ax = plt.subplot(111)

    bar_locs = np.arange(len(stable_list))
    bar_stable = ax.bar(bar_locs - bar_width / 2, stable_list,
                         width=bar_width, label='stable', color='#6699FF')  # plot bar
    bar_switch = ax.bar(bar_locs + bar_width / 2, switch_list,
                         width=bar_width, label='switch', color='#660033')
    ax.set_xticks(bar_locs)
    ax.set_xticklabels(['anti-correlated', 'decorrelated', 'correlated'], rotation=0) # ax_bar.set_xticklabels(inds_sel.keys())
    ax.legend(); ax.set_ylabel('Fraction of neurons');
    ax.set_title('Distribution of stable & switch neurons', weight='bold')
    # sns.despine()
    if save_fig:
        plt.savefig(fig_name, bbox_inches='tight')
    return ax

def plot_neuron_diff(ax_select, act_1, act_2, mean_ls='-',
                     time_labels=double_time_labels_blank[:-1]):
    ax_select.axvspan(xmin=1.5, xmax=3.5, color='grey', alpha=0.3)
    ax_select.axvspan(xmin=5.5, xmax=7.5, color='grey', alpha=0.3)
    ax_select.axvspan(xmin=9.5, xmax=11.5, color='grey', alpha=0.3)
    ax_select.axvspan(xmin=13.5, xmax=15.5, color='grey', alpha=0.3)
    mean_act = (act_1 + act_2) / 2
    c_mat_green = ru.create_color_mat(x=act_1, c='green')
    c_mat_mag = ru.create_color_mat(x=act_1, c='m')
    c_mat_k = ru.create_color_mat(x=act_1, c='k')
    for ii in range(len(act_1) - 1):
        ax_select.plot(np.arange(ii, (ii + 2)), mean_act[ii:(ii + 2)],
                       linewidth=3, linestyle=mean_ls, c='k', alpha=0.8)#c=c_mat_k[ii, :])
        ax_select.plot(np.arange(ii, (ii + 2)), act_2[ii:(ii + 2)],
                       linewidth=5, c=c_mat_mag[ii, :]);
        ax_select.plot(np.arange(ii, (ii + 2)), act_1[ii:(ii + 2)],
                       c=c_mat_green[ii, :], linewidth=5);
    ax_select.set_xticks(np.arange(len(time_labels)));
    ax_select.set_xlabel('Time'); ax_select.set_ylabel('Activity')
    ax_select.set_xticklabels(time_labels);
    ax_select.set_ylim([-1, 1.3])
    for i_letter, letter in enumerate(['A', 'B', 'C', 'D']):
        ax_select.text(s=letter, x=1.8 + 4 * i_letter, y=1.15,
                       fontdict={'weight': 'bold', 'fontsize': 18})
    ax_select.spines['top'].set_visible(False)
    ax_select.spines['right'].set_visible(False)
    return ax_select

def plot_arrow_line(x, y, ax=None, c='blue', verbose=False, swap_x=False,
                    swap_y=False, draw_time=False, draw_names_sens_mem=False,
                    color_sense='#8da0cb', color_mem='#fc8d62',
                    sens_times=np.arange(2, 8), mem_times=np.arange(8, 11), draw_sens_mem=False):
    if ax is None:
        ax = plt.subplot(111)
    c_mat = ru.create_color_mat(x=x, c=c)
#     ax.quiver(x[:-1], y[:-1], x[1:]-x[:-1], y[1:]-y[:-1], width=.02,
#               scale_units='xy', angles='xy', scale=1, color=c_mat)
    if swap_y:
        y = -1 * y
    if swap_x:
        x = -1 * x
    x_sens_A = np.mean(x[sens_times[:2]])
    y_sens_A = np.mean(y[sens_times[:2]])
    x_sens_B = np.mean(x[sens_times[-2:]])
    y_sens_B = np.mean(y[sens_times[-2:]])
    x_mem = np.mean(x[mem_times])
    y_mem = np.mean(y[mem_times])
    if verbose:
        print('sens', x_sens.round(2), y_sens.round(2))
        print('mem', x_mem.round(2), y_mem.round(2))
    traj_width = {True: 3, False: 7}
    for ii in range(len(x) - 1): # plot trajectores
        ax.plot(x[ii:(ii + 2)], y[ii:(ii + 2)], c=c_mat[ii, :], linewidth=traj_width[draw_sens_mem], zorder=1)
#     ax.plot(x, y, color=c_mat)
    # plt.scatter(x_sens, y_sens, marker='x', s=50, c=c_mat[-1, :][np.newaxis, :])
    # plt.scatter(x_mem, y_mem, marker='o', s=50, c=c_mat[-1, :][np.newaxis, :])
    if draw_sens_mem:
        if c == 'm':
            total_sense_length = np.sqrt((x_sens_A + x_sens_B) ** 2 + (y_sens_A + y_sens_B) ** 2)
            arr_sens_A = patches.Arrow(x=0, y=0, dx=(x_sens_A + x_sens_B) / total_sense_length,
                                        dy=(y_sens_A + y_sens_B) / total_sense_length,
                                        color=color_sense, width=0.2, zorder=2)
            # arr_sens_B = patches.Arrow(x=0, y=0, dx=x_sens_B, dy=y_sens_B, color=color_sense, width=0.2, zorder=2)
            arr_mem = patches.Arrow(x=0, y=0, dx=x_mem / np.sqrt(x_mem ** 2 + y_mem ** 2),
                                    dy=y_mem / np.sqrt(x_mem ** 2 + y_mem ** 2), color=color_mem, width=0.2, zorder=2)
            ax.add_patch(arr_sens_A)
            # ax.add_patch(arr_sens_B)
            ax.add_patch(arr_mem)
            if draw_names_sens_mem == 'high':
                plt.text(s='sensory experience', x=0.2, y=0.8, c=color_sense)
                plt.text(s='correlated\nmemory', x=0.05, y=-0.3, c=color_mem)
            elif draw_names_sens_mem == 'med':
                plt.text(s='sensory experience', x=0.2, y=0.5, c=color_sense)
                plt.text(s='decorrelated\nmemory', x=0.35, y=-1, c=color_mem)
            elif draw_names_sens_mem == 'low':
                plt.text(s='sensory\nexperience', x=0.7, y=0.6, c=color_sense)
                plt.text(s='anti-correlated\nmemory', x=-1.2, y=-1.1, c=color_mem)
    if draw_time:
        if draw_time == 'high':
            time_arrow = patches.FancyArrowPatch(posA=(0.2, 0.9), posB=(1.05, 0.1),
                                                 arrowstyle="Simple, tail_width=0.5, head_width=4, head_length=8",
                                                 connectionstyle="arc3, rad=-0.5", **{'color' : 'grey'})
            ax.text(s='Time', x=0.85, y=0.8)
        elif draw_time == 'med':
            time_arrow = patches.FancyArrowPatch(posA=(0.2, 0.95), posB=(0.2, -0.8), zorder=-0.5,
                                                 arrowstyle="Simple, tail_width=0.5, head_width=4, head_length=8",
                                                 connectionstyle="arc3, rad=-1.15", **{'color' : 'grey'})
            ax.text(s='Time', x=0.75, y=0.7)
        elif draw_time == 'low':
            time_arrow = patches.FancyArrowPatch(posA=(0.15, 0.90), posB=(0.75, 0.15),
                                                 arrowstyle="Simple, tail_width=0.5, head_width=4, head_length=8",
                                                 connectionstyle="arc3, rad=-1", **{'color' : 'grey'})
            time_arrow_1 = patches.FancyArrowPatch(posA=(0.75, 0.15), posB=(0.05, -0.8),
                                                     arrowstyle="Simple, tail_width=0.5, head_width=4, head_length=8",
                                                     connectionstyle="arc3, rad=-0.2", **{'color' : 'grey'})
            time_arrow_2 = patches.FancyArrowPatch(posA=(-0.01, -0.82), posB=(-0.6, -0.1),
                                                  arrowstyle="Simple, tail_width=0.5, head_width=4, head_length=8",
                                                  connectionstyle="arc3, rad=-1.3", **{'color' : 'grey'})
            ax.add_patch(time_arrow_1)
            ax.add_patch(time_arrow_2)
            ax.text(s='Time', x=0.9, y=0.8)
        ax.add_patch(time_arrow)
    # ax.set_axis_off()
    # ax.get_xaxis().set_visible(False)
    ax.set_xticks([])

    # ax.get_yaxis().set_visible(False)
    ax.set_yticks([])

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    # ax.set_xlim([-1, 1]); ax.set_ylim([-1, 1])
    if swap_x:
        ax.text(s='-1', x=0.96, y=-0.15, fontdict={'fontsize': 12})
        ax.text(s='1', x=-1, y=-0.15, fontdict={'fontsize': 12})
    elif not swap_x:
        ax.text(s='1', x=1, y=-0.15, fontdict={'fontsize': 12})
        ax.text(s='-1', x=-1.02, y=-0.15, fontdict={'fontsize': 12})
    if swap_y:
        ax.text(s='-1', x=-0.16, y=0.96, fontdict={'fontsize': 12})
        ax.text(s='1', x=-0.12, y=-1.04, fontdict={'fontsize': 12})
    elif not swap_y:
        ax.text(s='1', x=-0.12, y=0.96, fontdict={'fontsize': 12})
        ax.text(s='-1', x=-0.16, y=-1.04, fontdict={'fontsize': 12})
    return ax

def plot_two_neuron_state_space(activity_1, activity_2, mean_ls_dict, swap_x=False, swap_y=False,
                                max_tp=17, ax=None, save_fig=False, font_size=16,
                                x_name='Stable neuron', y_name='Switch neuron',
                                draw_sens_mem=False, draw_time=False, draw_names_sens_mem=False,
                                fig_name='figures/example_med_statespace_stable-switch.pdf'):
    if ax is None:
        ax = plt.subplot(111)

    n1 = list(activity_1.keys())[0]
    n2 = list(activity_1.keys())[1]
    mean_n1 = (activity_1[n1] + activity_2[n1]) / 2
    mean_n2 = (activity_1[n2] + activity_2[n2]) / 2
    ax.plot([-1, 1], [0, 0], c='k', linewidth=2, linestyle=mean_ls_dict[1], zorder=0.5)  # x axis - so correpsonding to neuron on y axis
    ax.plot([0, 0], [-1, 1], c='k', linewidth=2, linestyle=mean_ls_dict[0], zorder=0.5)  # y axis - so correspond to neuron on x axis

    _ = plot_arrow_line(activity_1[n1][:max_tp] - mean_n1[:max_tp],
             activity_1[n2][:max_tp] - mean_n2[:max_tp], c='green',# draw_time=draw_time,
             draw_sens_mem=draw_sens_mem, ax=ax, swap_x=swap_x, swap_y=swap_y)
    _ = plot_arrow_line(activity_2[n1][:max_tp] - mean_n1[:max_tp],
             activity_2[n2][:max_tp] - mean_n2[:max_tp], c='m', draw_time=draw_time,
             draw_sens_mem=draw_sens_mem, ax=ax, swap_x=swap_x, swap_y=swap_y,
             draw_names_sens_mem=draw_names_sens_mem)
    # ax.set_title('State space', weight='bold')
    ax.text(s=x_name, x=0.65, y=-0.28,
               fontdict={'fontsize': font_size})
    ax.text(s=y_name, x=-0.4, y=1.15,
               fontdict={'fontsize': font_size})

    if save_fig:
        plt.savefig(fig_name, bbox_inches='tight')
    return ax


def plot_trial_activity(forw, ax, neuron_order=None, n_trial=0, c_bar=True, print_labels=False):
    tmp_act = forw['test'][n_trial, :, :].T
    if neuron_order is None:
        neuron_order is np.arange(tmp_act.shape[0])
    tmp_act = np.squeeze(tmp_act[neuron_order, :])
    sns.heatmap(tmp_act, vmin=-1, vmax=1, cmap='RdBu_r', cbar=c_bar,
                xticklabels=double_time_labels_blank[:-1], ax=ax,
                cbar_kws={'pad': 0.01, 'fraction': 0.01})
    bottom, top = ax.get_ylim()
    ax.set_ylim(bottom + 1.5, top - 0.5)
    if print_labels:
        ax.set_ylabel('neuron id'); ax.set_xlabel('time');
        ax.set_title(f'Activity of {forw["labels_test"][n_trial]} trial')
    return ax

def plot_convergence_rnn(rnn, save_fig=False, verbose=False,
                         fig_name='figures/convergence_training.pdf'):
    # plt.subplot(211)
    ax_conv = plot_train_test_perf(rnn_model=rnn, ax=plt.subplot(211), train=False)
    # plt.ylim([1.2, 2])
    ax_conv.text(s='Test loss during training', x=5, y=7, fontdict={'weight': 'bold'})
    ax_conv.set_ylabel('Total loss')

    ax_ratio_ce = plt.subplot(212)
    ax_ratio_ce.plot(np.arange(rnn.info_dict['trained_epochs']),
             np.zeros_like(rnn.test_loss_ratio_ce) + 0.5, c='grey', linestyle=':')
    ax_ratio_ce.plot(rnn.test_loss_ratio_ce, linewidth=3, c='k', linestyle='--')
    ax_ratio_ce.set_xlabel('Epoch'); ax_ratio_ce.set_ylabel('ratio CE loss');
    ax_ratio_ce.text(s='Ratio Cross Entropy / Total loss', x=5, y=0.8,
                     fontdict={'weight': 'bold'});
    # sns.despine()
    if verbose:
        print(f'Final test performance: {np.round(rnn.test_loss_arr[-1], 3)}')
    if save_fig:
        plt.savefig(fig_name, bbox_inches='tight')
    return(ax_conv, ax_ratio_ce)


def plot_multiple_rnn_properties(rnn_name_dict, rnn_folder):
    n_rnn = len(rnn_name_dict)
    n_panels = 5
    rnn = {}
    i_rnn = 0
    mean_ls_dict = {0: '-', 1: ':'}
    neuron_selection = {'low': [0, 19], 'med': [0, 5], 'high': [19, 2]}
    title_selection = {'low': ['neuron 0 (Switch)', 'neuron 19 (Switch)'],
                       'med': ['neuron 0 (Stable)', 'neuron 5 (Switch)'],
                       'high': ['neuron 19 (Stable)', 'neuron 2 (Stable)']}
    rnn_title_dict = {'low': 'C) Anti-correlated coding', 'med': 'B) Decorrelated coding',
                      'high': 'A) Correlated coding'}
    swap_x_dict = {'low': True, 'med': True, 'high': False}
    swap_y_dict = {'low': False, 'med': True, 'high': True}
    ax_rast, ax_single, ax_ss, ax_ss_arr, ax_ctmat, ol = {}, {}, {}, {}, {}, {}
    for key, rnn_name in rnn_name_dict.items():
        with open(rnn_folder + rnn_name, 'rb') as f:
            rnn[key] = pickle.load(f)
        _, __, forw  = bp.train_single_decoder_new_data(rnn=rnn[key], ratio_expected=0.5, sparsity_c=0.1)
        labels_use_1 = np.array([x[0] == '1' for x in forw['labels_test']])
        labels_use_2 = np.array([x[0] == '2' for x in forw['labels_test']])

        ## raster plot
        ax_rast[key] = plt.subplot(n_panels, n_rnn, 1 + i_rnn)
        ol[key] = plot_raster_trial_average(forw=forw, ax=ax_rast[key], reverse_order=(key == 'low'), c_bar=False)
        ax_rast[key].set_title(rnn_title_dict[key], weight='bold')
        ax_rast[key].set_xlabel('Time ' + r"$\to$")

        ## single examples
        ax_single[key] = {}  # plt.subplot(n_panels, n_rnn, 2 + (i_rnn * n_panels))
        activity_1, activity_2 = {}, {}
        for i_plot, n_neuron in enumerate([ol[key][neuron_selection[key][xx]] for xx in range(2)]): # two pre selected neurons
            ax_single[key][i_plot] = plt.subplot(n_panels * 2, n_rnn, 7 + (i_plot * 3) + i_rnn)
            activity_1[n_neuron] = forw['test'][labels_use_1, :, :][:, :, n_neuron].mean(0)
            activity_2[n_neuron] = forw['test'][labels_use_2, :, :][:, :, n_neuron].mean(0)
            ax_single[key][i_plot] = plot_neuron_diff(ax_select=ax_single[key][i_plot],
                                                      act_1=activity_1[n_neuron],
                                                      act_2=activity_2[n_neuron],
                                                      mean_ls=mean_ls_dict[i_plot])
            ax_single[key][i_plot].set_title(f'Example {title_selection[key][i_plot]}', weight='bold')
            ax_single[key][i_plot].set_ylim([-1, 1.65])
            ax_single[key][i_plot].set_ylabel('')
            ax_single[key][i_plot].set_xlabel('')
            if i_plot == 0:
                ax_single[key][i_plot].set_xticklabels(['' for x in range(len(double_time_labels_blank[:-1]))])

        ## state space
        ax_ss[key] = plt.subplot(n_panels, n_rnn, 7 + i_rnn)
        plot_two_neuron_state_space(activity_1=activity_1, activity_2=activity_2, font_size=10,
                                   mean_ls_dict=mean_ls_dict, save_fig=False, ax=ax_ss[key],
                                   swap_x=swap_x_dict[key], swap_y=swap_y_dict[key],
                                   draw_time=key,
                                   x_name=title_selection[key][0][-7:-1] + ' neuron',
                                   y_name=title_selection[key][1][-7:-1] + ' neuron')
        # ax_ss[key].set_xlim([-1, 1])
        # ax_ss[key].set_ylim([-1, 1])


        ## state space with arrows
        ax_ss_arr[key] = plt.subplot(n_panels, n_rnn, 10 + i_rnn)
        plot_two_neuron_state_space(activity_1=activity_1, activity_2=activity_2, font_size=10,
                                    mean_ls_dict=mean_ls_dict, save_fig=False, ax=ax_ss_arr[key],
                                    swap_x=swap_x_dict[key], swap_y=swap_y_dict[key],
                                    draw_sens_mem=True, x_name=title_selection[key][0][-7:-1] + ' neuron',
                                    y_name=title_selection[key][1][-7:-1] + ' neuron',
                                    draw_names_sens_mem=key)
        # ax_ss_arr[key].set_xlim([-0.9, 0.9])
        # ax_ss_arr[key].set_ylim([-0.9, 0.9])

        ## CT matrix
        ax_ctmat[key] = plt.subplot(n_panels, n_rnn, 13 + i_rnn)
        _, hm = plot_decoder_crosstemp_perf(score_matrix=rnn[key].decoding_crosstemp_score['alpha'],
                               ax=ax_ctmat[key], c_bar=False,
                               ticklabels=double_time_labels_blank[:-1])
        ax_ctmat[key].set_title('')

        if i_rnn == 0:
            ax_rast[key].set_ylabel('i) raster plot colour preference', weight='bold')
            ax_single[key][1].set_ylabel('ii) example neurons', weight='bold', y=1.2)
            ax_ss[key].set_ylabel('iii) state space of \nexample neurons \n ', weight='bold')
            ax_ss_arr[key].set_ylabel('iv) switch cells rotate \nmemory representation\n ', weight='bold')
            ax_ctmat[key].set_ylabel('v) cross-temporal \ndecoding accuracy', weight='bold')

        elif i_rnn == (n_rnn - 1):
            ## Color bar raster  matrix:
            divider = make_axes_locatable(ax_rast[key])
            cax_rast = divider.append_axes('right', size='5%', pad=0.01)
            mpl_colorbar(ax_rast[key].get_children()[0], cax=cax_rast)
            cax_rast.yaxis.set_ticks_position('right')

            ## Color bar ct matrix:
            divider = make_axes_locatable(ax_ctmat[key])
            cax_ct = divider.append_axes('right', size='5%', pad=0.01)
            mpl_colorbar(hm.get_children()[0], cax=cax_ct)
            cax_ct.yaxis.set_ticks_position('right')

        i_rnn += 1
    return None

def plot_prediction_example(rnn, verbose=1, plot_conv=True):

    ## Generate new test trials:
    if verbose:
        print(f'generating data with {rnn.info_dict["ratio_train"]} train ratio, {rnn.info_dict["ratio_exp"]} expected ratio')
    tmp0, tmp1 = bp.generate_synt_data(n_total=100,
                                   n_times=rnn.info_dict['n_times'],
                                   n_freq=rnn.info_dict['n_freq'],
                                   ratio_train=rnn.info_dict['ratio_train'],
                                   ratio_exp=rnn.info_dict['ratio_exp'],
                                   noise_scale=rnn.info_dict['noise_scale'],
                                   double_length=rnn.info_dict['doublesse'])
    x_train, y_train, x_test, y_test = tmp0
    labels_train, labels_test = tmp1
    _, __, forward_mat = bp.train_decoder(rnn_model=rnn, x_train=x_train, x_test=x_test,
                                       labels_train=labels_train, labels_test=labels_test,
                                       save_inplace=False, sparsity_c=0.1, label_name='alpha')  # train decoder just to get forward matrix really
    forward_mat['labels_train'] = labels_train
    forward_mat['labels_test'] = labels_test


    fig = plt.figure(constrained_layout=False)
    if plot_conv is True:
        plot_conv = 1
        gs = fig.add_gridspec(ncols=3, nrows=2, width_ratios=[1, 2.2, 1.2], left=0.32, right=1)
        gs_bottom = fig.add_gridspec(ncols=1, nrows=3, left=0, right=0.22, hspace=0.4)
    else:
        plot_conv = 0
        gs = fig.add_gridspec(ncols=3, nrows=2, width_ratios=[1, 2.2, 1.2])


    ax_gt, ax_act, ax_pred = {}, {}, {}
    ind_exp, true_exp, pred_exp = {}, {}, {}
    for i_ind, ind in enumerate(['11', '12']):
        ind_exp[ind] = np.where(labels_test == ind)[0][0]
        pred_exp[ind] = bp.compute_full_pred(x_test[ind_exp[ind],:,:], model=rnn)  # computed forward predictions
        true_exp[ind] = y_test[ind_exp[ind], :, :]
        pred_exp[ind] = pred_exp[ind].squeeze()
        true_exp[ind] = true_exp[ind].squeeze()
        assert pred_exp[ind].ndim == true_exp[ind].ndim and pred_exp[ind].ndim == 2, 'pred_exp or true_exp doesnt have dim 2, probably because it is mutliple trials'
        pred_exp[ind] = pred_exp[ind].detach().numpy()
        true_exp[ind] = true_exp[ind].detach().numpy()

        if i_ind == 0:  # sort neurons
            eval_times = rnn.info_dict['eval_times']
            non_eval_times = np.array(list(set(np.arange(eval_times[-1])).difference(set(eval_times))))
            pred_exp[ind][non_eval_times, :] = 0  # set non-clamped time points to 0
            ol = opt_leaf(forward_mat['test'][ind_exp[ind], :, :].T)  # optimal leaf sorting
            forward_mat['test'] = forward_mat['test'][:, :, ol]

        ax_gt[ind] = fig.add_subplot(gs[i_ind, 0])  # stimuli
        plot_example_trial(true_exp[ind], ax=ax_gt[ind], c_map='Greys', print_labels=False, c_bar=False)

        ax_act[ind] = fig.add_subplot(gs[i_ind, 1])  # activity
        plot_trial_activity(forw=forward_mat, ax=ax_act[ind], n_trial=ind_exp[ind], c_bar=False)

        ax_pred[ind] = fig.add_subplot(gs[i_ind, 2])  # predictions
        plot_example_trial(pred_exp[ind], ax=ax_pred[ind], c_map='Greys', print_labels=False, c_bar=False)

        ## C highlight:
        for ax in [ax_pred[ind], ax_gt[ind]]:
            ax.add_patch(patches.FancyBboxPatch((8.5, 4.85), width=2.9, height=2.45,
                                           fill=False, edgecolor='blue', lw=3))

        ## Colorbars
        if i_ind == 0:
            divider = make_axes_locatable(ax_pred[ind])
            cax_top = divider.append_axes('right', size='5%', pad=0.1)
            mpl_colorbar(ax_act[ind].get_children()[0], cax=cax_top)
            cax_top.yaxis.set_ticks_position('right')
            cax_top.set_yticks([-1, -0.5, 0, 0.5, 1])
            for tick in cax_top.yaxis.get_major_ticks():
                tick.label.set_fontsize('x-small')
            cax_top.set_ylabel('Neural activity')
        elif i_ind == 1:
            divider = make_axes_locatable(ax_pred[ind])
            cax_bottom = divider.append_axes('right', size='5%', pad=0.1)
            mpl_colorbar(ax_pred[ind].get_children()[0], cax=cax_bottom)
            cax_bottom.yaxis.set_ticks_position('right')
            cax_bottom.set_yticks(np.linspace(0, 1, 6))
            for tick in cax_bottom.yaxis.get_major_ticks():
                tick.label.set_fontsize('x-small')
            cax_bottom.set_ylabel('Probability')

        ## Labels and such:
        ax_act[ind].set_ylabel('neuron #')
        if i_ind == 0:
            ax_act[ind].set_title('Neural activity r' + r"$_t$", weight='bold')
            ax_gt[ind].set_title('True stimuli z' + r"$_t$", weight='bold')
            ax_gt[ind].set_ylabel(r"$\mathbf{\alpha = 1, \beta = 1}$" + '\n expected trial', weight='bold', size=12)
            ax_pred[ind].set_title('Network predictions ' + r"$\mathbf{\hat{y}}_t$", weight='bold')
            ax_act[ind].set_xlabel('')
        else:
            ax_act[ind].set_title('')
            ax_gt[ind].set_ylabel(r"$\mathbf{\alpha = 1, \beta = 2}$" + '\n unexpected trial', weight='bold', size=12)
            ax_gt[ind].set_xlabel('Time ' + r"$\to$", size=12)
            ax_act[ind].set_xlabel('Time ' + r"$\to$", size=12)
            ax_pred[ind].set_xlabel('Time ' + r"$\to$", size=12)

    if plot_conv == 1:
        ax_conv_top = fig.add_subplot(gs_bottom[0, 0])
        ax_conv_top = plot_train_test_perf(rnn_model=rnn, ax=ax_conv_top, train=False)
        ax_conv_top.set_ylabel('Total loss')

        ax_conv_middle = fig.add_subplot(gs_bottom[1, 0])
        ax_conv_middle = plot_train_test_perf(rnn_model=rnn, ax=ax_conv_middle, train=False)
        ax_conv_middle.set_ylabel('Total loss')

        ax_conv_bottom = fig.add_subplot(gs_bottom[2, 0])
        ax_conv_bottom.plot(np.arange(rnn.info_dict['trained_epochs']),
                 np.zeros_like(rnn.test_loss_ratio_ce) + 0.5, c='grey', linestyle=':')
        ax_conv_bottom.plot(rnn.test_loss_ratio_ce, linewidth=3, c='k', linestyle='--')
        ax_conv_bottom.set_xlabel('Epoch'); ax_conv_bottom.set_ylabel('ratio CE loss');
        for ax in [ax_conv_top, ax_conv_middle, ax_conv_bottom]:
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

    return (ax_gt, ax_act, ax_pred)

def plot_distr_networks(rnn_folder='models/75-25_100models/', verbose=0,
                        train_times = np.arange(8, 11),
                        test_times = np.arange(6, 8)):

    agg_score_alpha = bp.aggregate_score_mats(model_folder=rnn_folder, label='alpha')
    agg_score_beta = bp.aggregate_score_mats(model_folder=rnn_folder, label='beta')
    if verbose:
        print(f'shape agg: {agg_score_alpha.shape}')
        print(f'train times: {train_times}, test times: {test_times}')
    summ_accuracy = agg_score_alpha[:, train_times, :][:, :, test_times].mean((1, 2))  # average of patch
    alpha_diag = np.diag(agg_score_alpha.mean(0))
    beta_diag = np.diag(agg_score_beta.mean(0))
    alpha_diag_err = np.diag(agg_score_alpha.std(0))
    beta_diag_err = np.diag(agg_score_beta.std(0))
    ## draw fig:
    ax_mean = plt.subplot(1, 3, 1)   # mean ct
    plot_decoder_crosstemp_perf(score_matrix=agg_score_alpha.mean(0), cmap_hm='BrBG', c_bar=False,
                                   ax=ax_mean, ticklabels=double_time_labels_blank[:-1])
    ax_mean.set_title('Average ' + r'$\mathbf{\alpha}$' + ' accuracy\n(100 networks)', weight='bold')
    ## Custom color bar:
    divider = make_axes_locatable(ax_mean)
    cax_mean = divider.append_axes('right', size='5%', pad=0.01)
    mpl_colorbar(ax_mean.get_children()[0], cax=cax_mean)
    cax_mean.yaxis.set_ticks_position('right')
    for tick in cax_mean.yaxis.get_major_ticks():
        tick.label.set_fontsize('x-small')

    ax_var = plt.subplot(1, 3, 2)  # variance matrix
    plot_decoder_crosstemp_perf(score_matrix=agg_score_alpha.var(0), cmap_hm='bone_r', c_bar=False,
                                   ax=ax_var, ticklabels=double_time_labels_blank[:-1])
    ax_var.set_title('Variance ' + r'$\mathbf{\alpha}$' + ' accuracy', weight='bold')
    ## custom color bars:
    divider = make_axes_locatable(ax_var)
    cax_var = divider.append_axes('right', size='5%', pad=0.01)
    mpl_colorbar(ax_var.get_children()[0], cax=cax_var)
    cax_var.yaxis.set_ticks_position('right')
    for tick in cax_var.yaxis.get_major_ticks():
        tick.label.set_fontsize('x-small')

    ax_auto = plt.subplot(2, 3, 3)  # alpha and beta auto-decoding
    _  = plot_alpha_beta_performance(alpha_perf=alpha_diag, beta_perf=beta_diag, ax=ax_auto)
    ax_auto.fill_between(x=np.arange(len(alpha_diag)), y1=alpha_diag - alpha_diag_err,
                         y2=alpha_diag + alpha_diag_err, color='#018571', alpha=0.3)
    ax_auto.fill_between(x=np.arange(len(beta_diag)), y1=beta_diag - beta_diag_err,
                         y2=beta_diag + beta_diag_err, color='grey', alpha=0.3)
    ax_auto.set_title('Auto-temporal accuracy', weight='bold')


    ax_hist = plt.subplot(2, 3, 6)  # histogram
    ax_hist.set_xlabel('Average accuracy')
    ax_hist.set_ylabel('Frequency');
    ax_hist.set_title('Histogram of patch', weight='bold')
    n, bins, hist_patches = ax_hist.hist(summ_accuracy, color='k', bins=np.linspace(0, 1, 21),
                                         rwidth=0.9, alpha=0.9)
    ## Colour hist bars: https://stackoverflow.com/questions/23061657/plot-histogram-with-colors-taken-from-colormap
    cm = plt.cm.get_cmap('BrBG')
    bin_centers = 0.5 * (bins[:-1] + bins[1:])
    col = bin_centers - np.min(bin_centers)      # scale values to interval [0,1]
    col /= np.max(col)
    for c, p in zip(col, hist_patches):
        plt.setp(p, 'facecolor', cm(c))

    ax_hist.spines['top'].set_visible(False)
    ax_hist.spines['right'].set_visible(False)

    ## Add patches
    color_patch  = 'green'
    lw_patch = 2
    ax_mean.add_patch(patches.FancyBboxPatch((test_times[0], train_times[0]),
                                        width=len(test_times), height=len(train_times),
                                       fill=False, edgecolor=color_patch, lw=lw_patch))  # patch in variance plot
    ax_var.add_patch(patches.FancyBboxPatch((test_times[0], train_times[0]), zorder=1,
                                        width=len(test_times), height=len(train_times),
                                       fill=False, edgecolor=color_patch, lw=lw_patch))  # patch in variance plot
    ax_hist.add_patch(patches.FancyBboxPatch((0.01, -7),
                                    width=0.8, height=20.8, clip_on=False,
                                    fill=False, edgecolor=color_patch, lw=lw_patch)) # box around histogram
    line_top = patches.Arc(xy=(test_times[0] + 2, train_times[0] + 1.58), width=29.8, height=3.77,
                            theta1=270, theta2=360, clip_on=False, linewidth=lw_patch, color=color_patch) # top connecting line
    ax_var.add_patch(line_top)
    line_bottom = patches.Arc(xy=(test_times[0] + 2, train_times[0] + 12.55), width=29.8, height=18.5,
                            theta1=270, theta2=360, clip_on=False, linewidth=lw_patch, color=color_patch)  # bottom connecting line
    ax_var.add_patch(line_bottom)

    ax_mean.text(s='A', x=-2, y=-1, fontdict={'weight': 'bold', 'size': 'xx-large'})
    ax_mean.text(s='B', x=25, y=-1, fontdict={'weight': 'bold', 'size': 'xx-large'})
    ax_mean.text(s='C', x=50, y=-1, fontdict={'weight': 'bold', 'size': 'xx-large'})
    ax_mean.text(s='D', x=50, y=11.1, fontdict={'weight': 'bold', 'size': 'xx-large'}, zorder=2)
    return None
