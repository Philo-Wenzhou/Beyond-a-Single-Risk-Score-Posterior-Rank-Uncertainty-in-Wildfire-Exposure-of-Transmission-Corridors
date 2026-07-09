data {
  int<lower=1> N;
  int<lower=1> K;
  matrix[N, K] X;
  array[N] int<lower=0, upper=1> y;
  int<lower=1> N_new;
  matrix[N_new, K] X_new;
}
parameters {
  real alpha;
  vector[K] beta;
}
model {
  alpha ~ normal(0, 5);
  beta ~ normal(0, 2);
  y ~ bernoulli_logit(alpha + X * beta);
}
generated quantities {
  vector[N_new] p_new;
  for (n in 1:N_new) {
    p_new[n] = inv_logit(alpha + X_new[n] * beta);
  }
}
