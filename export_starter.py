import argparse

import vector_representations.preprocessing
from exporter import exporter
from properties.default_values import *
from properties.export_modes import *
from text_processing_tools.data_processing_tool import valid_date

parser = argparse.ArgumentParser(description="Help of export module")

parser.add_argument('-f', '--forum', help='Id of forum to export, you can check id of forum by starting script with argument -m forums')
parser.add_argument('-m', '--mode', help='Available modes: glove, tfidf, posts, forums, preprocess. Check readme for more information about the modes.', required=True)
parser.add_argument('-df', '--datefrom',
                    help='Posts written from the date, use format: y-m-d, default value: 1970-1-1',
                    type=valid_date)
parser.add_argument('-dt', '--dateto',
                    help='Posts written until the date, use format: y-m-d, default value: 2040-1-1',
                    type=valid_date)
parser.add_argument('-fn', '--filename', help='Filename for exported file, default value: output')

parser.add_argument('-gw', '--glovewindow', help='Size of context window in GloVe, default value: 5', type=int)
parser.add_argument('-gv', '--glovevector', help='Used vector dimension in GloVe, default value: 100', type=int)
parser.add_argument('-ni', '--niter', help='Number of iterations to train GloVe word vectors, default value: 100', type=int)
parser.add_argument('-mindf', '--mindf',
                    help='Min document frequency when creating dictionary for vector representation, default: 0.0025',
                    type=float)
parser.add_argument('-maxdf', '--maxdf',
                    help='Max document frequency when creating dictionary for vector representation, default: 0.5',
                    required=False, type=float)
args = parser.parse_args()

current_date = datetime.datetime.now().strftime("%d-%m-%Y-%H-%M")
mode = args.mode

if mode != forums_mode and args.forum is None:
    raise argparse.ArgumentTypeError("Forum id must be given when mode diferent from 'forums'!")

forum_id = None if mode == forums_mode else int(args.forum)
filename = "output" if args.filename is None else args.filename
filename = mode + "_" + filename + current_date + ".csv"

date_from = date_from if args.datefrom is None else args.datefrom
date_to = date_to if args.dateto is None else args.dateto
glove_window_size = glove_window_size if args.glovewindow is None else args.glovewindow
glove_vector_dimension = glove_vector_dimension if args.glovevector is None else args.glovevector
max_df = max_df if args.maxdf is None else args.maxdf
min_df = min_df if args.mindf is None else args.mindf
niter = niter if args.niter is None else args.niter


if mode == glove_mode:
    filename = "window_size_" + str(glove_window_size) + "_vec_dim_" + str(glove_vector_dimension) + "_" + filename
    exporter.do_glove(forum_id, date_from, date_to, filename, glove_window_size, glove_vector_dimension, max_df, min_df, niter)
elif mode == tfidf_mode:
    exporter.do_tfidf(forum_id, date_from, date_to, filename, max_df, min_df)
elif mode == preprocess_mode:
    vector_representations.preprocessing.preprocess_texts_from_given_forum(forum_id, date_from, date_to, filename)
elif mode == posts_mode:
    exporter.export_posts(forum_id, date_from, date_to, filename)
elif mode == forums_mode:
    exporter.show_all_forums()
else:
    print("No such mode - choose from:" + all_modes)
