# -*- coding: utf-8 -*-
"""Analysh_Eikonas.ipynb

# Ανάλυση Εικόνας
## Υπολογιστική Εργασία 2023-2024



*   Κυριάκος Κίχης, Π20013
*   Χρίστος Ξύδης, Π20008

## Περιεχόμενα



0.   Initial setup
1.   Preparing dataset
2.   Downloading and preparing pretrained model
3.   Algorithm implementation
4.   Extracting features and running the algorithm
5.   Visualizing results from the example
6.   Accuracy metrics

## 0. Initial Setup

"""

"""Στη συνέχεια κάνουμε install τις απαραίτητες βιβλιοθήκες."""

pip install hypernetx
pip install torch 
pip install torchvision 
pip install matplotlib 
pip install numpy 
pip install requests


"""Τέλος, κάνουμε import τις βιβλιοθήκες."""

import torch
import torch.nn as nn
from torchvision import datasets, transforms,models
from torchvision.datasets import Documents
import matplotlib.pyplot as plt
import helper
import numpy as np
import random
import hypernetx as hnx
import requests

"""Προσθέτουμε ένα helper function για να προβάλλουμε τις εικόνες. """

url = "https://raw.githubusercontent.com/udacity/deep-learning-v2-pytorch/master/intro-to-pytorch/helper.py"
response = requests.get(url)

with open("helper.py", "wb") as f:
    f.write(response.content)


print("Setup complete")

"""## 1. Preparing the dataset

Αρχικά κατεβάζουμε το σύνολο των δεδομένων.
"""

data = Caltech101(root="./",download=True)

"""Στο παρακάτω κελί ετοιμάζουμε κάποιους μετασχηματισμούς ώστε οι εικόνες μας να μπορούν να δοθούν ως είσοδο στο νευρωνικο δίκτυο."""

transforms = transforms.Compose([transforms.Resize(255),  #resize
                                 transforms.CenterCrop(224),
                                 transforms.ToTensor()])  #cast to pytorch tensor type

"""Αποθηκεύουμε το μετασχηματισμένο σύνολο δεδομένων σε μια μεταβλητή."""

dataset = datasets.ImageFolder("/content/caltech101/101_ObjectCategories', transform=transforms)

"""Βλέπουμε το πλήθος εικόνων του dataset"""

len(dataset)

"""Επειδή ο αριθμός των εικόνων είναι μεγάλος κρατάμε μόνο ένα υποσύνολο από αυτές."""

dataset = list(dataset) #turn to list
random.shuffle(dataset)
keep_number = 2000

dataset = dataset[:keep_number]  #keep 2k images

"""Το σύνολο δεδομένων μας περιέχει εικόνες και το αντίστοιχο τους label, που είναι ένα σύνολο κατηγοριών/κλάσεων. Ξεχωρίζουμε τα labels από τις εικόνες αφού πρώτα ανακατέψουμε το dataset. """

images,labels = map(list, zip(*dataset))  #separate images from labels

"""Το παραπάνω βήμα ήταν σημαντικό καθώς θα χρησιμοποιήσουμε τα labels αργότερα κατά την μέτρηση της ακρίβειας.
Στη συνέχεια προβάλλουμε την πρώτη εικόνα του ανακατεμμένου συνόλου.
"""

helper.imshow(images[0],normalize=False)

"""## 2. Downloading and preparing a pretrained model.

Κατεβάζουμε ένα Vision Transformer με προεκπαιδευμένα βάρη που μας διαθέτει η pytorch, το βάζουμε στη GPU (αν υπάρχει) και παγώνουμε τα βάρη του για να μην αλλάξουν στις επόμενες εισόδους. Στο τέλος τυπώνουμε μια περιγραφή του δικτύου για να εξετάσουμε τη δομή του και να εντοπίσουμε το τελευταίο του επίπεδο
"""

model = models.vit_l_16(weights="DEFAULT")  #load pretrained network

device = "cuda" if torch.cuda.is_available() else "cpu" #set device as gpu if gpu is available

model.to(device)  #send model to chosen device

for param in model.parameters():  #freeze parameters
  param.requires_grad = False

print(model)  #print model summary

"""Βλέπουμε πως το τελευταίο επίπεδο είναι αυτό που βρίσκεται κάτω κάτω, οπότε το αντικαθιστούμε με ένα άδειο Sequential layer. Με τον τρόπο αυτό εξάγουμε τα χαρακτηρηστικά από το τελευταίο κρυφό επίπεδο. """

model.heads.head = nn.Sequential() #replace final layer

"""Στη συνέχεια εξάγουμε τα χαρακτηριστικά από την τελευταία εικόνα για να δούμε τις διαστάσεις τους και να βεβαιωθούμε πως το προηγούμενο βήμα έγινε σωστά."""

img = images[0] #get an image

features_var = model(img.unsqueeze(0).to(device))  #extract features
features = features_var.data

features.size()

"""Βλέπουμε πως τα χαρακτηριστικά έχουν διαστάσεις 1x1024.

## 3. Algorithm Implementation
### Log-based Hypergraph of Ranking References (LHRR) 
Τώρα θα υλοποιήσουμε τις συναρτήσεις που αποτελούν τα βήματα του αλγορίθμου.

#### α) Initial similarity
Για την αρχικό similarity των εικόνων χρησιμοποιούμε το αντίστροφο της Ευκλέιδειας απόστασης των feature vectors των εικόνων.
"""

def similarity_lists(features):  #original similarity function
  '''
  Computes the euclidean distance between every pair of features.

  features = list of features extracted from each image
  '''
  T = [[(0,0) for i in range(len(features))] for j in range(len(features))]
  for i in range(len(features)):
    for j in range(i,len(features)):
      #since the distance is also computed between a feature vector and itself, we add a small value to avoid a devide by zero error
      score = 1/(np.linalg.norm(features[i].cpu()-features[j].cpu())+0.00001) #inverse euclidean distance
      #use the fact that euclidean distance is symmetrical to speed up computation (a-b)^2 = (b-a)^2

      T[i][j]=(score,j) #since these lists will be sorted later, we keep the image index together with the score
      T[j][i]=(score,i) #so that we know which score corresponds to each image/feature vector
  return T

"""#### β) Rank normalization

Ως τιμή του L χρησιμοποιούμε όλο των αριθμό των εικόνων/χαρακτηριστικών καθώς έχουμε ήδη διαλέξει ένα υποσύνολο από τις αρχικές ~9000 εικόνες.
"""

def rank_normalization(features,T): # rank normalization
  '''
  Performs reciprocal rank normalization as defined in the paper (page 4)
  ρ_n(i,j) = 2L - (τ_i(j)+τ_j(i)),
  for each list τ in T, then sorts τ.

  features = list of features extracted from each image
  T = list of lists of distances
  '''
  L = len(features)
  for i in range(len(T)): #compute score for each pair
    for j in range(i,len(T)):
      score = 2*L - (T[i][j][0] + T[j][i][0])
      T[i][j] = (score,j)
      T[j][i] = (score,i)
  T = [sorted(t,key = lambda x: x[0]) for t in T]  #sort each sublist
  return T

"""#### γ) Hyperedge construction

Για την κατασκευή των υπερακμών θεωρήσαμε (όπως προτάθηκε και στην τάξη), κάθε υπερακμή να είναι κεντραρισμένη σε μία εικόνα. Συνεπώς θα υπάρχουν όσες υπερακμές όσες και οι εικόνες μας (2000) και η κάθε υπερακμή θα περιέχει τις k εικόνες με το χαμηλότερο distance που προέκυψαν από το Rank Normalization. Σε κάθε περίπτωση ο πρώτος γείτονας στην υπερακμή i θα είναι η εικόνα i, οπότε τελικά η ένωση όλων των συνόλων των κόμβων των υπερακμών θα ισούται πάντα με το V.
"""

def make_hyperedges(T,k): #make e_i
  '''
  Creates hyperedges as lists of nodes.
  Hyperedge e_i contains the first k nodes of T[i].

  T = list of sorted similarities for each pair of image features
  k = size of neighborhood
  '''
  E = []  #empty list of hyperedges
  for t in T: #for each sublist
    temp = []
    for p in t[:k]: #for the top k pairs
      temp.append(p[1]) #get the second value (index) of the pair
    E.append(temp)
  return E  #return list of hyperedges

"""#### δ) Association/Incidence matrix

Κατασκευάζουμε τον πίνακα association χρησιμοποιώντας τη διαφοροποίηση που εξηγήθηκε στην τάξη. Το βάρος του ζευγαριού e_i-Vj εξαρτάται από το αν ο κόμβος/εικόνα Vj βρίσκεται στους πρώτους k γείτονες της εικόνας Vi (δηλαδή τους κόμβους της υπερακμής e_i). Ο πρώτος από τους γείτονες (που είναι η ίδια η εικόνα) έχει βάρος 1 (log0) άρα η διαγώνιος αποτελείται από 1. Έπειτα τα βάρη μειώνονται σταδιακά. Αν δεν βρίσκεται στους πρώτους κ γείτονες έχει τιμή 0. 
"""

def association(E,V,T,k):
  '''
  Creates the association/incidence matrix r(e_i,v_j)=h(e_i,v_j).
  Based on pages 4,5 of the paper and info given in the class.

  Note: In our variation, since each hyperedge is centered around a node/image, it is clear that |E| = |V|. 
  Thus, the second parameter V can also be the list of hyperedges, since we only use its length. 

  E = list of hyperedges (each hyperedge is a list of nodes)
  V = list of nodes in the hypergraph
  T = list of sorted similarities for each pair of image features
  k = neighborhood size
  '''
  R = np.zeros((len(E),len(E)))
  for i,e in enumerate(E):  #for each edge
    for v in range(len(V)): #for each vertex
      if v in e:  #if vertex is in the hyperedge
        pos = e.index(v)+1  #get the position (+1 because counting in the paper starts from 1)
        R[i][v] = 1-np.math.log(pos,k+1)  #compute the weight
      else: #if vertex is not in the hyperedge
        R[i][v] = 0 #weight is 0
  return R

"""#### ε) Hypergraph construction

Εδώ κατασκευάζαμε το υπεργράφημα από τη λίστα των υπερακμών. Τελικά ωστόσο δεν χρειάστηκε το υπεργράφημα (εξήγηση υπάρχει στο σχόλιο Note: στο παραπάνω κελί) και επίσης δεν καταφέραμε ούτε να το οπτικοποιήσουμε (η draw function έβγαζε exception) οπότε η παρακάτω συνάρτηση δεν χρησιμοποιείται πουθενά.
"""

def make_hypergraph(E):
  '''
  Creates a hypergraph object using the HyperNetX library.

  E = list of hyperedges
  '''
  ed = {} #edge dictionary
  for i,e in enumerate(E):
    label = "e"+str(i)
    ed[label] = e
  HG = hnx.Hypergraph(ed)
  return HG

"""#### στ) Hyperedge weights
Εδώ υπολογίζουμε τα βάρη των υπερακμών με βάση των τύπο στο paper.
"""

def edge_weights(E,assoc):
  '''
  Computes edge weights as defined in page 6 of the paper.

  E = list of hyperedges
  assoc = association/incidence matrix H
  '''
  w = []
  for i,e in enumerate(E):  #for each hyperedge
    s=0
    for j in e: #for each node in the hyperedge
      s+= assoc[i][j]
    w.append(s)
  return w

"""#### ι) Hyperedge similarities

Εδώ υπολογίζουμε το pairwise similarity matrix με βάση τον τύπο στο paper.
"""

def hyperedge_similarities(assoc):  #Hyperedge Similarities
  '''
  Computes pairwise similarity matrix S as defined in page 6 of the paper.
  '''
  H = np.array(assoc)
  Sh = H @ H.T  # @ = matrix multiplication
  Su = H.T @ H
  S = np.multiply(Sh,Su)  # Hadamard product
  return S

"""#### ια) Membership degrees
Εδώ υπολογίζουμε τα membership degrees όπως και το paper. Αρχικά ορίζουμε και μια βοηθητική συνάρτηση που κατασκευάζει το καρτεσιανό γινόμενο μεταξύ 2 υπερακμών.
"""

def cartesian_product(eq,ei):
  '''
  Creates the cartesian product of 2 hyperedges (lists of nodes)

  eq, ei = hyperedges
  '''
  return np.transpose([np.tile(eq, len(ei)), np.repeat(eq, len(ei))])

def pairwise_similarity_relationship(w,assoc,E):
  '''
  Computes pairwise similarity relationship / membership degrees as defined in page 6 of the paper.

  w = hyperedge weights
  assoc = incidence/association matrix
  E = list of hyperedges
  '''

  # v_i, v_j in e_q^2 (cartesian product)
  #p(e_q,v_i,v_j) = |E| x |e_q^2| 
  
  p = [{} for _ in range(len(E))] #for each hyperedge create a dictionary with node pairs as keys
  for i,e in enumerate(E):
    cp3 = cartesian_product(e,e)
    for (v1,v2) in cp3:
      p[i][(v1,v2)] = w[i]*assoc[i][v1]*assoc[i][v2]
  return p

"""#### ιβ) Similarity based on the cartesian product.
Εδώ κατασκευάζουμε τον πίνακα c του paper (σελίδα 6).
"""

def make_C(E,p):
  '''
  Computes the similarity based on the cartesian product (page 6).

  E = list of hyperedges
  p = list of membership degrees for each pair in each hyperedge
  '''
  C = np.zeros((len(E),len(E)))
  for i,e in enumerate(E):  #for each hyperedge
    for (v1,v2) in p[i]:  #for each pair in the dict
      C[v1][v2]+=p[i][(v1,v2)]  #compute value
  return C

"""#### ιγ) Affinity matrix
Τέλος κατασκευάζουμε τον τελικό πίνακα W.
"""

def affinity_matrix(C,S):
  '''
  Computes final affinity matrix (page 6)
  '''
  return np.multiply(C,S)

"""#### ALL TOGETHER
Στο παρακάτω κελί ενώνουμε όλα τα επιμέρους βήματα του αλγορίθμου σε μία συνάρτηση.
"""

def LHRR(features,init_lists,k=3,num_iters=10):
  '''
  Entire LHRR algorithm put together

  features = list of features extracted from each image
  init_lists = initial similarity lists based on euclidean distance
  k = neighborhood size / hyperedge size
  num_iters = for how many iterations the algorithm will run
  '''

  for i in range(num_iters):

    T = rank_normalization(features,init_lists)  #perform rank normalization

    E = make_hyperedges(T,k)  #make hyperedges

    #HG = make_hypergraph(E)  #make hypergraph

    assoc = association(E,E,T,k)  #make association/incidence matrix 
    #There is an explanation above as to why E is passed two times

    w = edge_weights(E,assoc) #compute edge weights

    S = hyperedge_similarities(assoc) #compute hyper-edge similarities

    p = pairwise_similarity_relationship(w,assoc,E) #compute pairwise relationships

    C = make_C(E,p) #make the cartesian product based similarity matrix

    aff = affinity_matrix(C,S)  #compute the final matrix W

    # reshape final matrix so it becomes input of the next iteration
    aff = aff.tolist()

    for i,row in enumerate(aff):
      for j,v in enumerate(row):
        aff[i][j] = (aff[i][j],j) #add information about the index

    T = aff
  return aff

"""## 4. Extracting features and running the algorithm.

Αρχικά χρησιμοποιούμε το νευρωνικό για την εξαγωγή των χαρακτηρστικών.
"""

features = []

for img in images:
  features.append(model(img.unsqueeze(0).to(device))) #~1.5m for 2000 images with gpu


print(len(features))

#backup = features[:]

"""Στη συνέχεια τρέχουμε τον αλγόριθμο για 3 επαναλήψεις. Να σημειωθεί πως το αλγόριθμος παίρνει λίγη ώρα ~5-10 λεπτά καθώς δεν θεωρούμε συγκεκριμένες εικόνες ως query images, αλλά υπολογίζουμε τα σκορ για όλες τις εικόνες (2000). Η μεγάλη καθυστέρηση προκύπτει αρχικά όταν υπολογίζονται ευκλείδιες αποστάσεις για 2000*2000 feature vectors (όλα μεταξύ τους). Ωστόσο στο επόμενο βήμα μπορούμε να χρησιμοποιήσουμε οποιαδήποτε από τις 2000 εικόνες θέλουμε ως query image.

Τις αρχικές λίστες με τις αντίστροφες Ευκλείδιες αποστάσεις τις υπολογίζουμε εκτός του αλγορίθμου.
"""

init_lists = similarity_lists(features)

"""Έπειτα τρέχουμε τον αλγόριθμο."""

final_ranking = LHRR(features,init_lists,k=3,num_iters=3)  #final matrix W

"""## 5. Visualizing results from the example.

Εδώ εμφανίζουμε τα αποτελέσματα για την πρώτη εικόνα. Περισσότερα παραδείγματα υπάρχουν στο pdf.
"""

query_index = 0 #first image
retrieved = []  #keep indexes and scores of relevant images here
for (score,i) in final_ranking[query_index]:  #search first row of W
  if score!=0:  #if score is non zero
    retrieved.append((score,i))
retrieved = sorted(retrieved,key = lambda x: x[0],reverse=True) #sort by score

print(retrieved)

for (score,i) in retrieved[1:]:
  print(score,i)

"""Στην παραπάνω λίστα φαινόνται τα ζευγάρια (retrieved image score, retrieved image index). Προφανώς για την εικόνα 0 μεγαλύτερο σκορ έχει η ίδια η εικόνα 0. Στη συνέχεια προβάλουμε τις εικόνες με τη σειρά."""

helper.imshow(images[0],normalize=False)

helper.imshow(images[1876],normalize=False)

helper.imshow(images[436],normalize=False)

helper.imshow(images[1278],normalize=False)

"""Όπως φαίνεται, όλες οι εικόνες είναι εικόνες προσώπων (και μάλιστα του ίδου ανθρώπου) οπότε είναι relevant. Περισσότερα παραδείγματα εκτέλεσης στο pdf.

## 6. Accuracy metrics

Εδώ χρησιμοποιούμε precision και recall για να εκτιμήσουμε την ακρίβεια του αλγορίθμου. Δύο εικόνες θεωρούνται relevant/similar αν έχουν το ίδιο label. Υπολογίζουμε precision και recall για την εικόνα 0 (περισσότερα παραδείγματα στο pdf).
"""

def precision(query_index,final_ranking,labels,k=5):
  '''
  Compute precision using labels.

  index = index of query image
  final_ranking = affinity matrix W with final results
  labels = image labels
  k = number of retrieved images to keep
  '''

  retrieved = []
  for (score,i) in final_ranking[query_index]:
    if score!=0:  #get all non zero scores
      retrieved.append((score,i))
  retrieved = sorted(retrieved,key = lambda x: x[0],reverse=True) #sort based on scores

  retrieved = retrieved[1:k+1] #keep first k excluding the image itself which is always first

  true_label = labels[query_index]  #get target label
  c=0 #keep a counter
  for score,ix in retrieved:
    if labels[ix]==true_label:
      c+=1  #increment counter on correct label
  
  return c/len(retrieved) #return pct of correct labels

q_img = 0
p = precision(q_img,final_ranking,labels)
print("Precision for image "+str(q_img)+" is:",p)

"""Το precision βγαίνει 66% παρόλο που και οι 3 εικόνες είναι εικόνες προσώπων. Αυτό συμβαίνει επειδή υπάρχουν 2 ήδη labels για πρόσωπα: "faces" και "faces_easy" με ids 1 και 2 αντίστοιχα. Αν τυπώσουμε τα labels βλέπουμε πως 1 από τις 3 retrieved εικόνες έχει label=2 ενώ η query εικόνα και οι άλλες 2 retrieved έχουν label=1. Άρα P= 2/3 = 0.66"""

print("Query label: ",labels[0])

print("Retrieved image #1 label: ",labels[1876])

print("Retrieved image #2 label: ",labels[436])

print("Retrieved image #3 label: ",labels[1278])

"""Όσον αφορά τα ονόματα των labels στα οποία αντιστοιχούν τα παραπάνω ids, μπορούμε να κοιτάξουμε στο filestructure του dataset.
![image_2023-01-09_194916951.png](data:image/png;base64,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)

Ξεκινώντας την αρίθμηση από το 0 βλέπουμε πως οι κλάσεις "faces","faces_easy" έχουν ids 1,2 αντίστοιχα (υπάρχουν άλλες 98 κλάσεις αλλά δεν φαίνονται στην cropped εικόνα).
Περισσότερα παραδείγματα precision υπάρχουν στο pdf.

Στη συνέχεια κατασκευάζουμε το recall. Εξήγηση για τα αποτελέσματα, καθώς και περισσότερα παραδείγματα υπάρχουν στο pdf.
"""

def recall(query_index,final_ranking,labels):
  ixs = []
  for (score,i) in final_ranking[query_index]:  #get indexes of all retrieved images
    if score!=0:
      ixs.append(i)
  ixs = sorted(ixs,reverse=True)

  true_label = labels[query_index]
  c=0 #count correctly retrieved images
  for ix in ixs[1:]:
    if labels[ix]==true_label:
      c+=1

  db_c = 0  #count all images with same label as query image
  for l in labels:
    if l==true_label:
      db_c += 1
  
  return c/(db_c-1)

q_img = 0
r = recall(q_img,final_ranking,labels)
print("Recall for image "+str(q_img)+" is:",r)

"""Περισσότερα παραδείγματα υπάρχουν στο pdf."""