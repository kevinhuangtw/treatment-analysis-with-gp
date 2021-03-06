# %%
import numpy as np
import pandas as pd
import gpflow

from gpflow.utilities import print_summary
from progressbar import progressbar


# %%
def gp_predict(data, split_ratio, demean=True):
    # %% Const
    N = data.shape[0]
    D = sum(data.columns.str.startswith("x"))
    X_COLS = ["x" + str(i) for i in range(1, D + 1)]
    Y_COLS = ["y"]

    # %% Split Train/Test
    train_num = int(N * split_ratio)
    train = data.iloc[:train_num]
    test = data.iloc[train_num:]

    # %% Train GP Function
    def get_trained_gp(x_df, y_df, means=None):
        # Create Kernels
        k1 = gpflow.kernels.SquaredExponential(
            lengthscales=[0.1] * 5 + [0.2] * 5 + [1.0] * 10)
        k2 = gpflow.kernels.Linear()
        k = k1 + k2

        # Create GP Model
        m = gpflow.models.GPR(data=(x_df.values, y_df.values), kernel=k,
                              mean_function=(lambda x: means) if means else None)
        opt = gpflow.optimizers.Scipy()
        opt_logs = opt.minimize(m.training_loss, m.trainable_variables,
                                options=dict(maxiter=100))
        return m

    # %% Get Trained GP (for z = 0 and z = 1)
    train_z0 = train.loc[train["z"] == 0]
    train_z0_means = np.mean(train_z0[Y_COLS]).values if demean else None
    gp_z0 = get_trained_gp(train_z0[X_COLS], train_z0[Y_COLS],
                           means=train_z0_means)

    train_z1 = train.loc[train["z"] == 1]
    train_z1_means = np.mean(train_z1[Y_COLS]).values if demean else None
    gp_z1 = get_trained_gp(train_z1[X_COLS], train_z1[Y_COLS],
                           means=train_z1_means)

    # print_summary(gp_z0)
    # print_summary(gp_z1)

    # %% Predict
    for i, row in progressbar(test.iterrows()):
        # predict y0
        mean, var = gp_z0.predict_f(np.atleast_2d(row[X_COLS].values))
        test.loc[i, "y0_hat"] = mean.numpy().item()

        # predict y1
        mean, var = gp_z1.predict_f(np.atleast_2d(row[X_COLS].values))
        test.loc[i, "y1_hat"] = mean.numpy().item()

    # %% Policy Decision
    test["te"] = test["y1"] - test["y0"]
    test["te_hat"] = test["y1_hat"] - test["y0_hat"]

    test["t"] = (test["te"] < 0).astype(int)
    test["t_hat"] = (test["te_hat"] < 0).astype(int)

    # %%
    return test


if __name__ == "__main__":
    # %%
    data = pd.read_csv("data.csv")
    split_ratio = 0.6
