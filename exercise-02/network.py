import numpy as np
from sklearn import datasets

####################################

class ReLULayer(object):
    '''
    input: BxD
    '''
    def forward(self, input):
        # remember the input for later backpropagation
        self.input = input
        # return the ReLU of the input
        relu = np.maximum(0, input)
        return relu

    def backward(self, upstream_gradient):
        # compute the derivative of ReLU from upstream_gradient and the stored input
        downstream_gradient = upstream_gradient * (self.input > 0)
        return downstream_gradient

    def update(self, learning_rate):
        pass # ReLU is parameter-free

####################################

class OutputLayer(object):
    def __init__(self, n_classes):
        self.n_classes = n_classes

    def forward(self, input):
        # remember the input for later backpropagation
        self.input = input
        # return the softmax of the input
        softmax = np.exp(input) / np.sum(np.exp(input), axis=1, keepdims=True)
        return softmax

    def backward(self, predicted_posteriors, true_labels):
        # return the loss derivative with respect to the stored inputs
        # (use cross-entropy loss and the chain rule for softmax,
        #  as derived in the lecture)
        def get_one_hot(targets, nb_classes):
            res = np.eye(nb_classes)[np.array(targets).reshape(-1)]
            return res.reshape(list(targets.shape)+[nb_classes])
        
        one_hot_labels = get_one_hot(true_labels, self.n_classes)
        downstream_gradient = predicted_posteriors - one_hot_labels
        return downstream_gradient

    def update(self, learning_rate):
        pass # softmax is parameter-free

####################################


class LinearLayer(object):
    def __init__(self, n_inputs, n_outputs):
        self.n_inputs  = n_inputs
        self.n_outputs = n_outputs
        # randomly initialize weights and intercepts
        self.B = np.random.normal(0, 0.01, (n_inputs, n_outputs))
        self.b = np.random.normal(0, 0.01, (n_outputs,))

    def forward(self, input):
        # remember the input for later backpropagation
        self.input = input
        # compute the scalar product of input and weights
        # (these are the preactivations for the subsequent non-linear layer)
        preactivations = self.input @ self.B + self.b # your code here
        return preactivations

    def backward(self, upstream_gradient):
        # compute the derivative of the weights from
        # upstream_gradient and the stored input
        self.grad_b = np.sum(upstream_gradient, axis=0) / upstream_gradient.shape[0] # your code here
        self.grad_B = self.input.T @ upstream_gradient # your code here
        # compute the downstream gradient to be passed to the preceding layer
        downstream_gradient = upstream_gradient @ self.B.T # your code here
        return downstream_gradient

    def update(self, learning_rate):
        # update the weights by batch gradient descent
        self.B = self.B - learning_rate * self.grad_B
        self.b = self.b - learning_rate * self.grad_b

####################################

class MLP(object):
    def __init__(self, n_features, layer_sizes):
        # constuct a multi-layer perceptron
        # with ReLU activation in the hidden layers and softmax output
        # (i.e. it predicts the posterior probability of a classification problem)
        #
        # n_features: number of inputs
        # len(layer_size): number of layers
        # layer_size[k]: number of neurons in layer k
        # (specifically: layer_sizes[-1] is the number of classes)
        self.n_layers = len(layer_sizes)
        self.layers   = []

        # create interior layers (linear + ReLU)
        n_in = n_features
        for n_out in layer_sizes[:-1]:
            self.layers.append(LinearLayer(n_in, n_out))
            self.layers.append(ReLULayer())
            n_in = n_out

        # create last linear layer + output layer
        n_out = layer_sizes[-1]
        self.layers.append(LinearLayer(n_in, n_out))
        self.layers.append(OutputLayer(n_out))

    def forward(self, X):
        # X is a mini-batch of instances
        batch_size = X.shape[0]
        # flatten the other dimensions of X (in case instances are images)
        X = X.reshape(batch_size, -1)

        # compute the forward pass
        # (implicitly stores internal activations for later backpropagation)
        result = X
        for layer in self.layers:
            result = layer.forward(result)
        return result

    def backward(self, predicted_posteriors, true_classes):
        # perform backpropagation w.r.t. the prediction for the latest mini-batch X
        upstream_gradient = self.layers[-1].backward(predicted_posteriors, true_classes)
        for layer in reversed(self.layers[:-1]):
            upstream_gradient = layer.backward(upstream_gradient)


    def update(self, X, Y, learning_rate):
        posteriors = self.forward(X)
        predicted_classes = np.argmax(posteriors, axis=1)
        self.backward(posteriors, Y)
        for layer in self.layers:
            layer.update(learning_rate)

    def train(self, x, y, n_epochs, batch_size, learning_rate):
        N = len(x)
        n_batches = N // batch_size
        for i in range(n_epochs):
            print("Epoch", i)
            # reorder data for every epoch
            # (i.e. sample mini-batches without replacement)
            permutation = np.random.permutation(N)

            for batch in range(n_batches):
                # create mini-batch
                start = batch * batch_size
                x_batch = x[permutation[start:start+batch_size]]
                y_batch = y[permutation[start:start+batch_size]]

                # perform one forward and backward pass and update network parameters
                self.update(x_batch, y_batch, learning_rate)

##################################

if __name__=="__main__":

    # set training/test set size
    N = 2000

    # create training and test data
    X_train, Y_train = datasets.make_moons(N, noise=0.05)
    X_test,  Y_test  = datasets.make_moons(N, noise=0.05)
    n_features = 2 ## TODO try 4 networks here
    n_classes  = 2

    # standardize features to be in [-1, 1]
    offset  = X_train.min(axis=0)
    scaling = X_train.max(axis=0) - offset
    X_train = ((X_train - offset) / scaling - 0.5) * 2.0
    X_test  = ((X_test  - offset) / scaling - 0.5) * 2.0

    # set hyperparameters (play with these!)
    layer_sizes_multiple_mlps = [[2, 2, n_classes],
                                 [3, 3, n_classes],
                                 [5, 5, n_classes],
                                 [30, 30, n_classes]]
    
    n_epochs = 5
    batch_size = 200
    learning_rate = 0.05
    # create networks
    for layer_sizes in layer_sizes_multiple_mlps:
        print("MLP with layer_sizes:", layer_sizes)
        network = MLP(n_features, layer_sizes)

        # train
        network.train(X_train, Y_train, n_epochs, batch_size, learning_rate)

        # test
        predicted_posteriors = network.forward(X_test)
        # determine class predictions from posteriors by winner-takes-all rule
        predicted_classes = np.argmax(predicted_posteriors, axis=1) # your code here
        # compute and output the error rate of predicted_classes
        error_rate = np.sum(predicted_classes != Y_test) / len(Y_test) # your code here
        print("error rate:", error_rate)