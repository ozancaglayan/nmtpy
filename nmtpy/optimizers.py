'''
SGD and variants.
'''
import numpy as np

import theano
import theano.tensor as tensor

from .nmtutils import itemlist

# optimizers
# name(hyperp, tparams, grads, inputs (list), cost) = f_grad_shared, f_update
def adam(lr, tparams, grads, inp, cost, profile=False, mode=None):
    gshared = [theano.shared(p.get_value() * 0.,
                             name='%s_grad' % k)
               for k, p in tparams.iteritems()]

    gsup = [(gs, g) for gs, g in zip(gshared, grads)]
    f_grad_shared = theano.function(inp, cost, updates=gsup, profile=profile, mode=mode)

    lr0 = 0.0002
    b1 = 0.9
    b2 = 0.999
    e = 1e-8

    updates = []

    i = theano.shared(np.float32(0.))
    i_t = i + 1.

    bias_cor_1 = 1. - b1**(i_t)
    bias_cor_2 = 1. - b2**(i_t)
    lr_t = lr0 * (tensor.sqrt(bias_cor_2) / bias_cor_1)

    for p, g in zip(tparams.values(), gshared):
        m = theano.shared(p.get_value() * 0.)
        v = theano.shared(p.get_value() * 0.)

        m_t = (b1 * m) + ((1. - b1) * g)
        updates.append((m, m_t))
        v_t = (b2 * v) + ((1. - b2) * tensor.sqr(g))
        updates.append((v, v_t))

        p_t = p - (lr_t * (m_t / (tensor.sqrt(v_t) + e)))
        updates.append((p, p_t))

    updates.append((i, i_t))

    f_update = theano.function([lr], [], updates=updates, on_unused_input='ignore', profile=profile, mode=mode)

    return f_grad_shared, f_update


def adadelta(lr, tparams, grads, inp, cost, profile=False, mode=None):
    zipped_grads = [theano.shared(p.get_value() * np.float32(0.),
                                  name='%s_grad' % k)
                    for k, p in tparams.iteritems()]
    running_up2 = [theano.shared(p.get_value() * np.float32(0.),
                                 name='%s_rup2' % k)
                   for k, p in tparams.iteritems()]
    running_grads2 = [theano.shared(p.get_value() * np.float32(0.),
                                    name='%s_rgrad2' % k)
                      for k, p in tparams.iteritems()]

    zgup = [(zg, g) for zg, g in zip(zipped_grads, grads)]
    rg2up = [(rg2, 0.95 * rg2 + 0.05 * (g ** 2))
             for rg2, g in zip(running_grads2, grads)]

    f_grad_shared = theano.function(inp, cost, updates=zgup+rg2up,
                                    profile=profile, mode=mode)

    updir = [-tensor.sqrt(ru2 + 1e-6) / tensor.sqrt(rg2 + 1e-6) * zg
             for zg, ru2, rg2 in zip(zipped_grads,
                                     running_up2,
                                     running_grads2)]
    ru2up = [(ru2, 0.95 * ru2 + 0.05 * (ud ** 2))
             for ru2, ud in zip(running_up2, updir)]
    param_up = [(p, p + ud) for p, ud in zip(itemlist(tparams), updir)]

    f_update = theano.function([lr], [], updates=ru2up+param_up,
                               on_unused_input='ignore', profile=profile, mode=mode)

    return f_grad_shared, f_update


def rmsprop(lr, tparams, grads, inp, cost, profile=False, mode=None):
    zipped_grads = [theano.shared(p.get_value() * np.float32(0.),
                                  name='%s_grad' % k)
                    for k, p in tparams.iteritems()]
    running_grads = [theano.shared(p.get_value() * np.float32(0.),
                                   name='%s_rgrad' % k)
                     for k, p in tparams.iteritems()]
    running_grads2 = [theano.shared(p.get_value() * np.float32(0.),
                                    name='%s_rgrad2' % k)
                      for k, p in tparams.iteritems()]

    zgup = [(zg, g) for zg, g in zip(zipped_grads, grads)]
    rgup = [(rg, 0.95 * rg + 0.05 * g) for rg, g in zip(running_grads, grads)]
    rg2up = [(rg2, 0.95 * rg2 + 0.05 * (g ** 2))
             for rg2, g in zip(running_grads2, grads)]

    f_grad_shared = theano.function(inp, cost, updates=zgup+rgup+rg2up,
                                    profile=profile, mode=mode)

    updir = [theano.shared(p.get_value() * np.float32(0.),
                           name='%s_updir' % k)
             for k, p in tparams.iteritems()]
    updir_new = [(ud, 0.9 * ud - 1e-4 * zg / tensor.sqrt(rg2 - rg ** 2 + 1e-4))
                 for ud, zg, rg, rg2 in zip(updir, zipped_grads, running_grads,
                                            running_grads2)]
    param_up = [(p, p + udn[1])
                for p, udn in zip(itemlist(tparams), updir_new)]
    f_update = theano.function([lr], [], updates=updir_new+param_up,
                               on_unused_input='ignore', profile=profile, mode=mode)

    return f_grad_shared, f_update


def sgd(lr, tparams, grads, inp, cost, profile=False, mode=None):

    # allocate gradients and set them all to zero
    gshared = [theano.shared(p.get_value() * 0., name='%s_grad' % k)
               for k, p in tparams.iteritems()]

    # create gradient copying list,
    # from grads (tensor variable) to gshared (shared variable)
    gsup = [(gs, g) for gs, g in zip(gshared, grads)]

    # compile theano function to compute cost and copy gradients
    f_grad_shared = theano.function(inp, cost, updates=gsup,
                                    profile=profile, mode=mode)

    # define the update step rule
    pup = [(p, p - lr * g) for p, g in zip(itemlist(tparams), gshared)]

    # compile a function for update
    f_update = theano.function([lr], [], updates=pup, profile=profile, mode=mode)

    return f_grad_shared, f_update


