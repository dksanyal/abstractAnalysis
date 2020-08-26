The code pertains to the following paper:

Banerjee, S., Sanyal, D. K., Chattopadhyay, S., Bhowmick, P. K., & Das, P. (2020). Segmenting Scientific Abstracts into Discourse Categories: A Deep Learning-Based Approach for Sparse Labeled Data. arXiv preprint arXiv:2005.05414.

ABSTRACT
========
The abstract of a scientific paper distills the contents of the paper into a short paragraph. In the biomedical literature, it is customary to structure an abstract into discourse categories like BACKGROUND, OBJECTIVE, METHOD, RESULT, and CONCLUSION, but this segmentation is uncommon in other fields like computer science. Explicit categories could be helpful for more granular, that is, discourse-level search and recommendation. The sparsity of labeled data makes it challenging to construct supervised machine learning solutions for automatic discourse-level segmentation of abstracts in non-bio domains. In this paper, we address this problem using transfer learning. We define three discourse categories – BACKGROUND, TECHNIQUE, and OBSERVATION – for an abstract because these three categories are most common. We train a deep neural network on structured abstracts from PubMed, then fine-tune it on a small hand-labeled corpus of computer science papers.

We observe an accuracy of 75% on the test corpus of computer science papers. We also perform an ablation study to highlight the roles of the different parts of the model. Our method appears to be a promising solution to the automatic segmentation of abstracts, where the labeled data is sparse.
