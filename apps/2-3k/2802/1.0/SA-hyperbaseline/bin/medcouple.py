#!/usr/bin/python
# encoding=utf8

# medcouple.py ---

# Copyright  © 2015 Jordi GutiÃ©rrez Hermoso <jordigh@octave.org>

# Author: Jordi GutiÃ©rrez Hermoso

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import random

from itertools import tee, izip

def wmedian(A, W):
    """This computes the weighted median of array A with corresponding
    weights W.
    """

    AW = zip(A, W)
    n = len(AW)

    wtot = sum(W)

    beg = 0
    end = n - 1

    while True:
        mid = (beg + end)//2

        AW = sorted(AW, key = lambda x: x[0]) # A partial sort would suffice here

        trial = AW[mid][0]

        wleft = wright = 0
        for (a, w) in AW:
            if a < trial:
                wleft += w
            else:
                # This also includes a == trial, i.e. the "middle"
                # weight.
                wright += w

        if 2*wleft > wtot:
            end = mid
        elif 2*wright < wtot:
            beg = mid
        else:
            return trial


def medcouple_1d(X, eps1 = 2**-52, eps2 = 2**-1022):
    """Calculates the medcouple robust measure of skewness.

    Parameters
    ----------
    y : array-like, 1-d

    Returns
    -------
    mc : float
        The medcouple statistic

    .. [1] G. Brys, M. Hubert, and A. Struyf "A Robust Measure of
    Skewness." Journal of Computational and Graphical Statistics, Vol.
    13, No. 4 (Dec., 2004), pp. 996- 1017

    .. [2] D. B. Johnson and T. Mizoguchi "Selecting the Kth Element
    in $X + Y$ and $X_1 + X_2 + \cdots X_m$". SIAM Journal of
    Computing, Vol. 7, No. 2 (May 1978), pp. 147-53.

    """
    # FIXME: Figure out what to do about NaNs.

    n = len(X)
    n2 = (n - 1)//2

    if n < 3:
        return 0

    Z = sorted(X, reverse=True)

    if n % 2 == 1:
        Zmed = Z[n2]
    else:
        Zmed = (Z[n2] + Z[n2 + 1])/2

    #Check if the median is at the edges up to relative epsilon
    if abs(Z[0] - Zmed) < eps1*(eps1 + abs(Zmed)):
        return -1.0
    if abs(Z[-1] - Zmed) < eps1*(eps1 + abs(Zmed)):
        return 1.0

    # Centre Z wrt median, so that median(Z) = 0.
    Z = [z - Zmed for z in Z]

    # Scale inside [-0.5, 0.5], for greater numerical stability.
    Zden = 2*max(Z[0], -Z[-1])
    Z = [z/Zden for z in Z]
    Zmed /= Zden

    Zeps = eps1*(eps1 + abs(Zmed))

    # These overlap on the entries that are tied with the median
    Zplus   = [z for z in Z if z >= -Zeps]
    Zminus  = [z for z in Z if Zeps >= z]

    n_plus = len(Zplus)
    n_minus = len(Zminus)


    def h_kern(i, j):
        """Kernel function h for the medcouple, closing over the values of
        Zplus and Zminus just defined above.

        In case a and be are within epsilon of the median, the kernel
        is the signum of their position.

        """
        a = Zplus[i]
        b = Zminus[j]

        if abs(a - b) <= 2*eps2:
            h = signum(n_plus - 1 -  i - j)
        else:
            h = (a + b)/(a - b)

        return h

    # Init left and right borders
    L = [0]*n_plus
    R = [n_minus - 1]*n_plus

    Ltot = 0
    Rtot = n_minus*n_plus
    medc_idx = Rtot//2

    # kth pair algorithm (Johnson & Mizoguchi)
    while Rtot - Ltot > n_plus:

        # First, compute the median inside the given bounds
        # (Be stingy, reuse same generator)
        [I1, I2] = tee(i for i in xrange(0, n_plus) if L[i] <= R[i])

        A = [h_kern(i, (L[i] + R[i])//2) for i in I1]
        W = [R[i] - L[i] + 1 for i in I2]
        Am = wmedian(A, W)

        Am_eps = eps1*(eps1 + abs(Am))

        # Compute new left and right boundaries, based on the weighted
        # median
        P = []
        Q = []

        j = 0
        for i in xrange(n_plus - 1, -1, -1):
            while j < n_minus and h_kern(i, j) - Am > Am_eps:
                j += 1
            P.append(j - 1)

        P.reverse()

        j = n_minus - 1
        for i in xrange(0, n_plus):
            while j >= 0 and h_kern(i, j) - Am < -Am_eps:
                j -= 1
            Q.append(j + 1)

        # Check on which side of those bounds the desired median of
        # the whole matrix may be.
        sumP = sum(P) + len(P)
        sumQ = sum(Q)

        if medc_idx <= sumP - 1:
            R = P
            Rtot = sumP
        else:
            if medc_idx > sumQ - 1:
                L = Q
                Ltot = sumQ
            else:
                return Am

    # Didn't find the median, but now we have a very small search
    # space to find it in, just between the left and right boundaries.
    # This space is of size Rtot - Ltot which is <= n_plus
    A = []
    for (i, (l, r)) in enumerate(izip(L, R)):
        for j in xrange(l, r + 1):
            A.append(h_kern(i, j))

    A.sort()     # A partial sort would suffice here
    A.reverse()

    Am = A[medc_idx - Ltot]

    return Am


def signum(x):
    if x > 0:
        return 1
    if x < 0:
        return -1
    else:
        return 0


def main():
    import sys
    fname = sys.argv[1]
    with open(fname) as f:
        data = [float(x) for x in f.readlines() if x.strip() != ""]

    print "%.16g" % medcouple_1d(data)

if __name__ == "__main__":
    main()
