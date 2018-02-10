#########################################################
#import packages
#########################################################
print "importing libraries"
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from copy import deepcopy
import numpy 
import opengm
import time 
from math import sqrt
import scipy.io
import numpy.linalg
from sklearn.cluster import KMeans
from sklearn import mixture
import vigra
from vigra import graphs
import h5py
from sklearn.decomposition import PCA
import itertools
import ThermalImagingAnalysis as tai
import ActivityPatterns as ap


###########################################################
#####################load   data##########################
###########################################################
f = h5py.File("626510_sep.mat", "r")
S1024_raw = numpy.array(f["S1024"].value)
dt, nopixels  = S1024_raw.shape
S1024_raw =  S1024_raw.reshape((S1024_raw.shape[0], -1))
f.close()
S1024_raw = S1024_raw.T

###########################################################
#####################define basis matrix####################
###########################################################
num_knots = 200
X = numpy.linspace(0, dt - 1, dt)
no_of_splines = num_knots
order_of_spline = 3
knots = numpy.linspace(0, 1, 1 + no_of_splines - order_of_spline)
difference = numpy.diff(knots[:2])[0]
x = (numpy.ravel(deepcopy(X)) - X[0]) / float(X[-1] - X[0])
x = numpy.r_[x, 0., 1.]
x = numpy.r_[x]
x = numpy.atleast_2d(x).T
n = len(x)
corner = numpy.arange(1, order_of_spline + 1) * difference
new_knots = numpy.r_[-corner[::-1], knots, 1 + corner]
new_knots[-1] += 1e-9
basis = (x >= new_knots[:-1]).astype(numpy.int) * (x < new_knots[1:]).astype(numpy.int)
basis[-1] = basis[-2][::-1]
maxi = len(new_knots) - 1
for m in range(2, order_of_spline + 2):
    maxi -= 1
    mask_l = new_knots[m - 1 : maxi + m - 1] != new_knots[:maxi]
    mask_r = new_knots[m : maxi + m] != new_knots[1 : maxi + 1]
    left_numerator = (x - new_knots[:maxi][mask_l]) * basis[:, :maxi][:, mask_l]
    left_denominator = new_knots[m-1 : maxi+m-1][mask_l] - new_knots[:maxi][mask_l]
    left = numpy.zeros((n, maxi))
    left[:, mask_l] = left_numerator/left_denominator
    right_numerator = (new_knots[m : maxi+m][mask_r]-x) * basis[:, 1:maxi+1][:, mask_r]
    right_denominator = new_knots[m:maxi+m][mask_r] - new_knots[1 : maxi+1][mask_r]
    right = numpy.zeros((n, maxi))
    right[:, mask_r] = right_numerator/right_denominator
    prev_bases = basis[-2:]
    basis = left + right
        
basis = basis[:-2] 

###########################################################
#####################penalise spline#######################
###########################################################
lambda_param = 0.02
D = numpy.identity(basis.shape[1])
D_k = numpy.diff(D,n=1,axis=-1)  
spline_coeff_raw = numpy.linalg.solve(numpy.dot(basis.T,basis)+lambda_param*numpy.dot(D_k,D_k.T),numpy.dot(basis.T,S1024_raw.T))


###########################################################
############Principal component analysis  #################
###########################################################
pca = PCA(n_components=num_knots)
pca.fit(spline_coeff_raw.T)
var1= numpy.cumsum(numpy.round(pca.explained_variance_ratio_, decimals=2)*100)
components = numpy.argmax(numpy.unique(var1)) + 1
pca = PCA(n_components=components)
pca.fit(spline_coeff_raw.T)
eigenvector_matrix = pca.components_
spline_coeff_raw = spline_coeff_raw.T.dot(eigenvector_matrix.T)

###########################################################
############Determining number of clusters  ###############
###########################################################
# range_n_clusters = range(1, 80)
# aic_list = []
# for n_clusters in range_n_clusters:
      # model = mixture.GaussianMixture(n_components=n_clusters, init_params='kmeans')
      # model.fit(spline_coeff_raw)
      # aic_list.append(model.aic(spline_coeff_raw))
	  
# plt.plot(range_n_clusters, aic_list, marker='o')
# plt.show()


###########################################################
############   Discretization    ##########################
###########################################################
num_clusters = 10
gmm = mixture.GaussianMixture(n_components=num_clusters)
t0=time.time()
gmm.fit(spline_coeff_raw)
t1=time.time()
print "Time taken for discretization of raw data is: ", t1-t0
labels = gmm.predict(spline_coeff_raw)
imgplot = plt.imshow(labels.reshape(640,480).transpose())
plt.show()
means  = gmm.means_
means_inv_PCA = eigenvector_matrix.T.dot(means.T)


########################################################
############## MRF graphical model######################
########################################################
n_labels_pixels = num_clusters
n_pixels=nopixels
def fast_norm(x):
    return sqrt(x.dot(x.conj()))

#define pixel unaries 
pixel_unaries = numpy.zeros((n_pixels,n_labels_pixels),dtype=numpy.float32)
for i in range(n_pixels):
    for l in range(n_labels_pixels):
        pixel_unaries[i,l] = fast_norm(S1024_raw.T[:,i] - basis.dot(means_inv_PCA[:,l])) #L2 norm
     

#define pixel regularizer
pixel_regularizer = opengm.differenceFunction(shape=[n_labels_pixels,n_labels_pixels],norm=1,weight=1.0/n_labels_pixels,truncate=None)

#initialise graphical model
gm = opengm.graphicalModel([n_labels_pixels]*n_pixels)

#pixel wise unary factors
fids = gm.addFunctions(pixel_unaries)
gm.addFactors(fids,numpy.arange(n_pixels))

#pixel wise pairwise factors
fid = gm.addFunction(pixel_regularizer)
vis = opengm.secondOrderGridVis(640,480)
gm.addFactors(fid,vis)


########################################################
############## Inference   #############################
########################################################
inf_trws=opengm.inference.TrwsExternal(gm, parameter=opengm.InfParam(steps=50))
visitor=inf_trws.timingVisitor()
t0=time.time()
inf_trws.infer(visitor)
t1=time.time()
argmin=inf_trws.arg()

print "energy ",gm.evaluate(argmin)
print "bound", inf_trws.bound()
result=argmin.reshape(640,480).transpose()
imgplot = plt.imshow(result)
plt.title('TRWS')
plt.show()
centroid_labels = numpy.zeros((n_pixels,num_knots))
centroid_labels = [means[i,:] for i in argmin]
centroid_labels = numpy.asarray(centroid_labels)
inv_pca_coeff = eigenvector_matrix.T.dot(centroid_labels.T)
Y_hat_mrf = basis.dot(inv_pca_coeff)
plt.imshow(Y_hat_mrf[0,:].reshape(640,480).transpose())
plt.show()

###########################################################
############## Semiparametric regression   ################
###########################################################

pPenalty = "Penalty_Gaussian_1024fr_2.5Hz_TruncatedWaveletBasis.mat"
pData = "626510_sep.mat"

f = h5py.File(pData, "r")
S = f["S1024"].value
T = f["T1024"].value
f_P = h5py.File(pPenalty, "r")
P = f_P["BPdir2"].value   # learned penalty matrix
print('[INFO] P is being transposed\n')
P = P.transpose() # P appears to be stored as transposed version of itself
B = f_P["B"].value        # basis matrix
S2 = S[0:1024,]
T2 = T[0:1024,]
Y_hat_mrf = Y_hat_mrf[0:1024,]
del S;
del T;

X = ap.computeGaussianActivityPattern(numpy.squeeze(T2)).transpose();
Z = tai.semiparamRegression(S2 - Y_hat_mrf, X, B, P);

plt.imshow(Z.reshape(640,480).transpose())
plt.show()

with h5py.File("Z_10_Clust.h5","w") as f:
  d1 = f.create_dataset('Z',data=Z)


#######################################################################
######################Evaluation#######################################
#######################################################################
groundtruthImg = numpy.array(f["groundtruthImg"].value)
groundtruth_foreground = numpy.where(groundtruthImg > 0)[0]
groundtruth_background = numpy.where(groundtruthImg == 0)[0]

true_positive =  len(numpy.where(abs(Z[groundtruth_foreground,]) >= 5.2)[0])                                  
false_positive = len(numpy.where(abs(Z[groundtruth_foreground,]) < 5.2)[0])

true_negative = len(numpy.where(abs(Z[groundtruth_background,]) < 5.2)[0])
false_negative = len(numpy.where(abs(Z[groundtruth_background,]) >= 5.2)[0])


true_positive_rate = true_positive / numpy.float32(true_positive + false_negative)
false_positive_rate = false_positive / numpy.float32(false_positive + true_negative)
accuracy  = (true_positive + true_negative) / numpy.float32(len(groundtruth_background) + len(groundtruth_foreground))
