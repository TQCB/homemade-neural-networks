import numpy as np

################################################################################

# Module containing definitions of different layers for our neural networks.
# Layers at a minimum define forward and backward pass methods. These 
# respectively apply the layer's calculations to an input, passing the result to
# the next layer and propagating the error to the previous layer.

# TODO
#  |- HIGH
#      |- Embedding
#      |- Attention
#  |- NORMAL
#      |- Recurrent
#      |- Convolutional 

################################################################################

class Layer:
  def __init__(self, input_dim, output_dim):
    self.weights = np.random.uniform(-1, 1, size=(input_dim, output_dim))
    self.bias = np.random.uniform(-1, 1,size=output_dim) - 0.5
    
  # compute h(X) = Y
  def forward(self, input):
    self.input = input
    self.output = np.dot(self.input, self.weights) + self.bias
    return self.output

  # compute dE/dX for dE/dY and update dX
  def backward(self, output_error, learning_rate):
    input_error = np.dot(output_error, self.weights.T)
    weights_error = np.dot(self.input.T, output_error)
    
    self.weights -= learning_rate * weights_error
    self.bias -= learning_rate * bias_error
        
    return input_error
    
class ActivationLayer(Layer):
  def __init__(self, activation):
    self.activation = activation()

  # compute h(X) = Y
  def forward(self, input):
    self.input = input
    self.output = self.activation.forward(self.input)
    return self.output
    
    # compute dE/dX for dE/dY 
  def backward(self, output_error, learning_rate):
    return self.activation.backward(self.input) * output_error
    
class FCLayer(Layer):
  def __init__(self, input_dim, output_dim):
    self.weights = np.random.rand(input_dim, output_dim) - 0.5
    self.bias = np.random.rand(1, output_dim) - 0.5
        
  def forward(self, input):
    self.input = input
    self.output = np.dot(self.input, self.weights) + self.bias
    return self.output
    
  def backward(self, output_error, learning_rate):
    input_error = np.dot(output_error, self.weights.T)
    weights_error = np.dot(self.input.T, output_error)
        
    # Calculate the gradient of the bias by summing over the batch dimension (axis=0)
    bias_error = np.sum(output_error, axis=0, keepdims=True)
        
    self.weights -= learning_rate * weights_error
    self.bias -= learning_rate * bias_error
    return input_error
    
class MultiHeadAttention(Layer):
  """
  Multi Head Self Attention for Dense networks.
    
  Args:
		input dim: Dimension of input (most likely the sequence len)
		n_dim: Total dimensions for Q, K, V matrices
		n_heads: Quantity of attention heads
  """
    
  def __init__(self, input_dim, n_dim, n_heads):
    self.n_heads = n_heads
    self.n_dim = n_dim
    self.head_dim = n_dim // n_heads # dims for qkv per head
    
    # Initialize weights for Q, K, V
    self.wq = np.random.rand(input_dim, self.n_dim) - 0.5
    self.wk = np.random.rand(input_dim, self.n_dim) - 0.5
    self.wv = np.random.rand(input_dim, self.n_dim) - 0.5
    
    # Output projection weights
    self.wo = np.random.rand(self.n_dim, self.n_dim) - 0.5
    
  def split_heads(self, x):
    """Utility function to split global Q, K, V into (n_heads, seq_len, head_dim)"""
    seq_len = x.shape[0]
    return x.reshape(self.n_heads, seq_len, self.head_dim)
    
  def combine_heads(self, x):
    """Utility function to combine head Q, K, V into (seq_len, n_dim)"""
    seq_len = x.shape[1]
    return x.reshape(seq_len, self.n_dim)
  
  def forward(self, input):
    """
    Forward pass through attention layer.
    
    Algo:
			- Initiate QKV and output projection matrices
			- Separate these matrices between the heads
			- Calculate scores: (QK.t)
				- Scale by d**0.5 for gradient stability and normalization WRT d
			- Calculate softmax of scores: exp(scores) / sum(exp(scores))
				- Substract max(scores) from the softmax for numerical stability
			- Calculate attention ouput: softmax(QK.t)V
			- Combine all head outputs
			- Project attention output into original space with output projection matrix
				-softmax(QK.t)VO
    
    """
    self.input = input
    
    # Compute Q, K, V
    # shape: (seq_len, output_dim)
    self.Q = np.dot(self.input, self.wq)
    self.K = np.dot(self.input, self.wk)
    self.V = np.dot(self.input, self.wv)
    
    # Split Q, K, V into heads
    # shape: (n_heads, seq_len, head_dim)
    self.Q = self.split_heads(self.Q)
    self.K = self.split_heads(self.K)
    self.V = self.split_heads(self.V)
    
    # Compute Luong attention (scaled dot product)
    # Divide by sqrt(d) for more stable gradient flow
    # Normalizes the magnitude of score with respect to d
    # shape: (n_heads, seq_len, seq_len)
    # score of each Q to each K, each element of sequence to every other
    scores = np.matmul(self.Q, self.K.transpose(0, 2, 1)) / np.sqrt(self.head_dim)
    
    # Softmax scores
    # shape: (n_heads, seq_len, seq_len)
    self.attention_weights = np.exp(scores - np.max(scores, axis=-1, keepdims=True))
    self.attention_weights /= np.sum(self.attention_weights, axis=-1, keepdims=True)
    
    # Get weighted sum of V by attention_weights
    # shape: (n_heads, seq_len, head_dims)
    attention_output = np.matmul(self.attention_weights, self.V)
    
    # Combine head outputs
    # shape: (seq_len, n_dim)
    concat_output = self.combine_heads(attention_output)
    
    # Final output projection
    # shape: (seq_len, n_dim)
    self.output = np.dot(concat_output, self.wo)
    return self.output
  
  def backward(self, output_error, learning_rate):
    """
    Backward pass through attention layer.
    """
    
    # Gradient of output projection layer Wo
    # shape: (n_dim, n_dim)
    d_wo = np.dot(self.combine_heads(np.matmul(self.attention_weights, self.V)).T, output_error)
    # shape: (seq_len, n_dim)
    combined_output_error = np.dot(output_error, self.wo.T)

    # Split error between heads
    # shape: (n_heads, seq_len, head_dim)
    output_error_heads = self.split_heads(combined_output_error)

    # Backprop through weighted sum
    d_attention_weights = np.matmul(output_error_heads, self.V.transpose(0, 2, 1))
    d_V = np.matmul(self.attention_weights.transpose(0, 2, 1), output_error_heads)

    # Backprop through softmax
    d_scores = self.attention_weights * (d_attention_weights - np.sum(self.attention_weights * d_attention_weights, axis=-1, keepdims=True))

    # Backprop through scaling
    d_scores /= np.sqrt(self.head_dim)

    # Backprop through QK^T
    d_Q = np.matmul(d_scores, self.K)
    d_K = np.matmul(d_scores.transpose(0, 2, 1), self.Q)

    # Combine gradients for each head
    d_Q_combined = self.combine_heads(d_Q)
    d_K_combined = self.combine_heads(d_K)
    d_V_combined = self.combine_heads(d_V)
    
    # Backprop through Q, K, V projections
    d_wq = np.dot(self.input.T, d_Q_combined)
    d_wk = np.dot(self.input.T, d_K_combined)
    d_wv = np.dot(self.input.T, d_V_combined)

    # Input error
    d_input = np.dot(d_Q_combined, self.wq.T) + np.dot(d_K_combined, self.wk.T) + np.dot(d_V_combined, self.wv.T)

    # Update weights
    self.wq -= learning_rate * d_wq
    self.wk -= learning_rate * d_wk
    self.wv -= learning_rate * d_wv
    self.wo -= learning_rate * d_wo

    return d_input