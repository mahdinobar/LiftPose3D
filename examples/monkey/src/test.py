import numpy as np
import src.utils as utils
from tqdm import tqdm
from torch.autograd import Variable


def test(test_loader, model, criterion, stat):
    losses = utils.AverageMeter()

    model.eval()

    all_dist, all_output, all_target, all_input = [], [], [], []

    for i, (inps, tars) in enumerate(tqdm(test_loader)):
        inputs = Variable(inps.cuda())
        targets = Variable(tars.cuda(non_blocking=True))

        # make prediction with model
        outputs = model(inputs)

        # outputs = outputs.view(outputs.size(0), -1)
        # targets = targets.view(targets.size(0), -1)

        # calculate loss
        loss = criterion(outputs, targets)
        losses.update(loss.item(), inputs.size(0))

        # undo normalisation to calculate accuracy in real units
        dim = 3
        # dimensions = stat['targets_3d']
        tar = utils.unNormalizeData(
            targets.data.cpu().numpy(), stat["mean"], stat["std"]
        )
        out = utils.unNormalizeData(
            outputs.data.cpu().numpy(), stat["mean"], stat["std"]
        )

        abserr = np.abs(out - tar) 

        n_pts = 39 // dim
        distance = np.zeros((abserr.shape[0], n_pts))
        for k in range(n_pts):
            distance[:, k] = np.sum(abserr[:, dim * k : dim * (k + 1)], axis=1)

        # group and stack
        all_dist.append(distance)
        all_output.append(outputs.data.cpu().numpy())
        all_target.append(targets.data.cpu().numpy())
        all_input.append(inputs.data.cpu().numpy())

    all_dist, all_output, all_target, all_input = (
        np.vstack(all_dist),
        np.vstack(all_output),
        np.vstack(all_target),
        np.vstack(all_input),
    )

    # mean errors
    all_dist[all_dist == 0] = np.nan
    joint_err = np.nanmean(all_dist, axis=0)
    ttl_err = np.nanmean(joint_err)

    print(">>> error: {} <<<".format(ttl_err))
    return losses.avg, ttl_err, joint_err, all_dist, all_output, all_target, all_input
