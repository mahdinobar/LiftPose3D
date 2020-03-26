#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 23 09:38:30 2020

@author: adamgosztolai
"""

import numpy as np
import src.utils as utils
import time
from src import Bar
from torch.autograd import Variable
from src.procrustes import get_transformation
from src.normalize import unNormalizeData


def test(test_loader, model, criterion, stat_3d, procrustes=False):
    losses = utils.AverageMeter()

    model.eval()

    all_dist, all_output, all_target = [], [], []
    start = time.time()
    batch_time = 0
    bar = Bar('>>>', fill='>', max=len(test_loader))

    for i, (inps, tars) in enumerate(test_loader):
        inputs = Variable(inps.cuda())
        targets = Variable(tars.cuda(non_blocking=True))

        #make prediction with model
        outputs = model(inputs)

        # calculate loss
        loss = criterion(outputs, targets)
        losses.update(loss.item(), inputs.size(0))

        # calculate arruracy
        targets = unNormalizeData(targets.data.cpu().numpy(), stat_3d['mean'], stat_3d['std'], stat_3d['dim_use'])
        outputs = unNormalizeData(outputs.data.cpu().numpy(), stat_3d['mean'], stat_3d['std'], stat_3d['dim_use'])

        outputs = outputs[:, stat_3d['dim_use']]
        targets = targets[:, stat_3d['dim_use']]

        if procrustes:
            for ba in range(inps.size(0)):
                gt = targets[ba].reshape(-1, 3)
                out = outputs[ba].reshape(-1, 3)
                _, Z, T, b, c = get_transformation(gt, out, True)
                out = (b * out.dot(T)) + c
                outputs[ba, :] = out.reshape(1, 51)

        sqerr = (outputs - targets) ** 2

        n_pts = int(len(stat_3d['dim_use'])/3)
        distance = np.zeros((sqerr.shape[0], n_pts))
        for k in np.arange(0, n_pts):
            distance[:, k] = np.sqrt(np.sum(sqerr[:, 3*k:3*k + 3], axis=1))
        
        all_dist.append(distance)
        all_output.append(outputs)
        all_target.append(targets)

        # update summary
        if (i + 1) % 100 == 0:
            batch_time = time.time() - start
            start = time.time()

        bar.suffix = '({batch}/{size}) | batch: {batchtime:.4}ms | Total: {ttl} | ETA: {eta:} | loss: {loss:.6f}' \
            .format(batch=i + 1,
                    size=len(test_loader),
                    batchtime=batch_time * 10.0,
                    ttl=bar.elapsed_td,
                    eta=bar.eta_td,
                    loss=losses.avg)
        bar.next()

    all_dist, all_output, all_target = np.vstack(all_dist), np.vstack(all_output), np.vstack(all_target)
    joint_err = np.mean(all_dist, axis=0)
    ttl_err = np.mean(all_dist)

    bar.finish()
    print (">>> error: {} <<<".format(ttl_err))
    return losses.avg, ttl_err, joint_err, all_output, all_target