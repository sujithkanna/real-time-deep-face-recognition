from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf
from scipy import misc
import cv2
import matplotlib.pyplot as plt
import numpy as np
import argparse
import facenet
import detect_face
import os
from os.path import join as pjoin
import sys
import time
import copy
import math
import pickle
from sklearn.svm import SVC
from sklearn.externals import joblib

print('Creating networks and loading parameters')
with tf.Graph().as_default():
    gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.6)
    sess = tf.Session(config=tf.ConfigProto(gpu_options=gpu_options, log_device_placement=False))
    with sess.as_default():
        pnet, rnet, onet = detect_face.create_mtcnn(sess, '')

        minsize = 20  # minimum size of face
        threshold = [0.6, 0.7, 0.7]  # three steps's threshold
        factor = 0.709  # scale factor
        margin = 44
        batch_size = 1000
        image_size = 182
        input_image_size = 160

        print('Loading feature extraction model')
        model_directory = 'facemodel.pb'
        facenet.load_model(model_directory)

        images_placeholder = tf.get_default_graph().get_tensor_by_name("input:0")
        embeddings = tf.get_default_graph().get_tensor_by_name("embeddings:0")
        phase_train_placeholder = tf.get_default_graph().get_tensor_by_name("phase_train:0")
        embedding_size = embeddings.get_shape()[1]

        classifier_filename = 'pkl/classifier.pkl'
        classifier_filename_exp = os.path.expanduser(classifier_filename)
        with open(classifier_filename_exp, 'rb') as infile:
            (model, class_names) = pickle.load(infile)
            print('load classifier file-> %s' % classifier_filename_exp)

        print('Start Recognition!')
        prevTime = 0
        # ret, frame = video_capture.read()
        frame = cv2.imread('abc.jpg', 0)
        frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)  # resize frame (optional)

        if frame.ndim == 2:
            frame = facenet.to_rgb(frame)
        frame = frame[:, :, 0:3]
        bounding_boxes, _ = detect_face.detect_face(frame, minsize, pnet, rnet, onet, threshold, factor)
        number_of_faces = bounding_boxes.shape[0]
        print('Detected_FaceNum: %d' % number_of_faces)

        if number_of_faces > 0:
            det = bounding_boxes[:, 0:4]
            img_size = np.asarray(frame.shape)[0:2]

            cropped = []
            scaled = []
            scaled_reshape = []
            bb = np.zeros((number_of_faces, 4), dtype=np.int32)

            for i in range(number_of_faces):
                emb_array = np.zeros((1, embedding_size))

                bb[i][0] = det[i][0]
                bb[i][1] = det[i][1]
                bb[i][2] = det[i][2]
                bb[i][3] = det[i][3]

                # inner exception
                if bb[i][0] <= 0 or bb[i][1] <= 0 or bb[i][2] >= len(frame[0]) or bb[i][3] >= len(frame):
                    print('face is inner of range!')
                    continue

                cropped.append(frame[bb[i][1]:bb[i][3], bb[i][0]:bb[i][2], :])
                cropped[0] = facenet.flip(cropped[0], False)
                scaled.append(misc.imresize(cropped[0], (image_size, image_size), interp='bilinear'))
                scaled[0] = cv2.resize(scaled[0], (input_image_size, input_image_size),
                                       interpolation=cv2.INTER_CUBIC)
                scaled[0] = facenet.prewhiten(scaled[0])
                scaled_reshape.append(scaled[0].reshape(-1, input_image_size, input_image_size, 3))
                feed_dict = {images_placeholder: scaled_reshape[0], phase_train_placeholder: False}
                emb_array[0, :] = sess.run(embeddings, feed_dict=feed_dict)
                predictions = model.predict_proba(emb_array)
                best_class_indices = np.argmax(predictions, axis=1)
                best_class_probabilities = predictions[np.arange(len(best_class_indices)), best_class_indices]
                cv2.rectangle(frame, (bb[i][0], bb[i][1]), (bb[i][2], bb[i][3]), (0, 255, 0), 2)  # boxing face

                print('Predictions', predictions)
                print('Indices', best_class_indices)
                print('Properties', best_class_probabilities)
                print('result: ', best_class_indices[0])
        else:
            print('Unable to align')
