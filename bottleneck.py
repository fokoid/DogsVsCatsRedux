"""Precomputes Inception bottlenecks from TFRecord files.

Running as a script purges tfrecord files before regenerating them.
"""

from glob import glob
import os.path

import tensorflow as tf

import dataset
import tfutil as tfu

FLAGS = {
        'MODEL_FILE':                   './inception/classify_image_graph_def.pb',
        'BOTTLENECK_DIR':               './bottleneck/',
        'BOTTLENECK_TENSOR_NAME':       'pool_3/_reshape:0',
        'RESIZED_INPUT_TENSOR_NAME':    'ResizeBilinear:0',
}

"""Remove any previous bottleneck files."""
def clean_all_bottlenecks():
    record_files = glob(os.path.join(FLAGS['BOTTLENECK_DIR'], '*.tfrecords'))
    for record_file in record_files:
        print('Removing {}'.format(record_file))
        os.remove(record_file)

def _write_bottleneck(sess, step, images, bottleneck_tensor, input_tensor, writer, **kwargs_unused):
    image = sess.run(tf.reshape(images, [1, 299, 299, 3]))
    bottleneck_value = sess.run(bottleneck_tensor, feed_dict={input_tensor: image})
    bottleneck_raw = bottleneck_value.flatten().tolist()
    example = tf.train.Example(features=tf.train.Features(feature={
        'bottleneck_value': tf.train.Feature(float_list=tf.train.FloatList(value=bottleneck_raw))
    }))
    writer.write(example.SerializeToString())

def save_bottlenecks(name, bottleneck_tensor, input_tensor):
    bottleneck_file = os.path.join(FLAGS['BOTTLENECK_DIR'], name + '.tfrecords')
    print('Saving bottlenecks to {}...'.format(bottleneck_file), end='')
    writer = tf.python_io.TFRecordWriter(bottleneck_file)
    images = tf.reshape(
        # predict=True means no shuffling (and no labels returned)
        dataset.inputs(name=name, num_epochs=1, batch_size=1, predict=True),
        [1, 299, 299, 3],
    )
    kwargs = {
            'images': images,
            'bottleneck_tensor': bottleneck_tensor,
            'input_tensor': input_tensor,
            'writer': writer,
            'name': name,
            }
    tfu.run_in_tf(func=_write_bottleneck, after=None, **kwargs)
    print('done.')

"""Save all bottlenecks."""
def save_all_bottlenecks():
    bottleneck_tensor, input_tensor = load_inception()
    for name in ['train', 'validation', 'test']:
        save_bottlenecks(name=name, bottleneck_tensor=bottleneck_tensor, input_tensor=input_tensor)

"""Load the Inception graph."""
def load_inception():
    reader = tf.WholeFileReader()
    graph_def = tf.GraphDef()
    with open(FLAGS['MODEL_FILE'], 'rb') as graph_file:
        graph_raw = graph_file.read()

    with tf.Session() as sess:
        graph_def.ParseFromString(graph_raw)
        bottleneck_tensor, resized_input_tensor = tf.import_graph_def(
            graph_def,
            name='',
            return_elements=[
                FLAGS['BOTTLENECK_TENSOR_NAME'],
                FLAGS['RESIZED_INPUT_TENSOR_NAME'],
                ]
            )
    return bottleneck_tensor, resized_input_tensor

if __name__ == '__main__':
    clean_all_bottlenecks()
    save_all_bottlenecks()