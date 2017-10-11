# Master-Thesis

The development of intraoperative imaging-guided neurosurgery represents a substantial improvement in the microsurgical treatment of malignant tissues in human brain. However, changes in regional cerebral blood flow greatly alter the emitted heat radiation of the cortex leading to a non-linear random behavior. Semi-parametric regression model adds the deterministic or parametric components of state-of-the-art Generalized Linear Models (GLM) with non-parametric components such as P-Splines to combat the non-linearity. However, in order to model spatial-temporal interactions in the thermographic brain imaging data, the semi-parametric regression using penalized splines has to be extended by a Markov random field (MRF) component. The MRF requires fast inference schemes such as Belief Propagation (BP), Tree-reweighted message passing (TRWS) etc in order to fulfill intra-operative performance requirements. Therefore, OpenGM framework is used to achieve this goal. The advancements proposed in this work will aid the neurosurgeons to achieve accurate removal of malignant tissues with minimal disruption of surrounding healthy neuronal matter.
