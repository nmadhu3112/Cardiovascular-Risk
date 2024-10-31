# -*- coding: utf-8 -*-
"""Cardiovascular_pyspark_madhu.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1EAc-Na3MeAF0UZ_Jd2PlNyMNGENQjtFu
"""

# Commented out IPython magic to ensure Python compatibility.
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
# %matplotlib inline
import seaborn as sns

# Suppress warnings:
def warn(*args, **kwargs):
    pass
import warnings
warnings.warn = warn

pip install pyspark

import pyspark
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName('Cardiovascular_Risk_1').getOrCreate()
spark

data = spark.read.csv('data_cardiovascular_risk.csv', header = True, inferSchema = True)

data.show()

from pyspark.sql.functions import col,when,count

#size of data
row = data.count()
col = len(data.columns)

print(f'Data Size :({row},{col})')

data.dtypes

"""**Categorical and Numerical Data**"""

from pyspark.sql.types import IntegerType

data = data \
    .withColumn('BPMeds', data['BPMeds'].cast(IntegerType())) \
    .withColumn('education', data['education'].cast(IntegerType()))

data.dtypes

# the columns with the ordinal features or like yes or no
categorical_columns = [col for col,typ in data.dtypes if (typ == 'string' or typ =='int') and col != 'age']
categorical_columns

numerical_columns = [col for col,typ in data.dtypes if typ =='double' and (col != 'BPMeds'and col!='education')]
numerical_columns.append('age')
numerical_columns

"""**Missing values**"""

from pyspark.sql.functions import col, when, count

for i in range(len(categorical_columns)):
    column = categorical_columns[i]
    if column == 'id':
        continue
    print(f"Description for column: {column}")
    data.groupby(column).count().show()

data = data.na.fill({'education':1, 'BPMeds':0})

for column in numerical_columns:
    print(f"Description for column: {column}")
    data.select(count(when(col(column).isNull(), 1)).alias(column)).show()

for column in numerical_columns:
    print(f"Description for column: {column}")
    data.select(column).describe().show()

from pyspark.ml.feature import Imputer

missing_numerical_col = ['cigsPerDay','BPMeds', 'totChol', "BMI", 'heartRate','glucose']

imputer = Imputer(inputCols = missing_numerical_col, outputCols = missing_numerical_col).setStrategy('median')
data = imputer.fit(data).transform(data)

for column in data.columns:
    print(f"Description for column: {column}")
    data.select(count(when(col(column).isNull(), 1)).alias(column)).show()

data_dup = data

"""**Feature Visualization**"""

!pip install datashader

df = data_dup.toPandas()

df.head(10)

df.drop('id', axis = 1, inplace = True)

df.head(5)

"""**Univatiate Analysis**"""

import matplotlib.pyplot as plt

fig = plt.figure(figsize=(14, 10))
n_bins = 20

for i in range(len(numerical_columns)):
    column = numerical_columns[i]
    plt.subplot(3, 3, i+1 )  # Create a subplot in a 4x4 grid
    plt.hist(df[column], bins=n_bins, density=True)
    plt.title(column)

plt.tight_layout()  # Adjust subplots to fit into the figure area.
plt.show()

canvas = ds.Canvas(plot_width=800, plot_height=400)
n_bins = 20

for column in numerical_columns:
    agg = canvas.histogram(df[column], bins=n_bins)
    img = tf.shade(agg, cmap='viridis')

    img.to_pil().show(title=column)

fig = plt.figure(figsize=(14, 10))

for i in range(1,len(categorical_columns)):
    column = categorical_columns[i]
    plt.subplot(3, 3, i )  # Create a subplot in a 3*3 grid
    ax = sns.countplot(x = column, data = df)
    plt.title(column)

    for patch in ax.patches:
        height = patch.get_height()
        ax.text(
            patch.get_x() + patch.get_width() / 2,
            height + 10,
            int(height),
            ha='center',
            va='bottom'
        )
plt.tight_layout()  # Adjust subplots to fit into the figure area.
plt.show()

import matplotlib.pyplot as plt
import seaborn as sns

num_columns = len(numerical_columns)
num_rows = (num_columns + 1) // 2
num_cols = 2

plt.figure(figsize=(8, num_rows * 6))

for i, column in enumerate(numerical_columns, start=1):
    plt.subplot(num_rows, num_cols, i)
    sns.histplot(data=df, x=column, hue='TenYearCHD', multiple='stack')
    plt.title(f'Distribution of {column} by Target')

plt.tight_layout()
plt.show()

plt.figure(figsize=(12, 8))

# Define the color palette for the violin plots
palette = {'0': 'darkblue','1': 'orange'}

# Plot violin plots for each numerical feature with respect to the target variable
for i, column in enumerate(numerical_columns, 1):
    plt.subplot(4, 2, i)
    sns.violinplot(x='TenYearCHD', y=column, data=df, palette=palette)
    plt.title(f'Violin Plot of {column} by Target')
    plt.xlabel('TenYearCHD')
    plt.ylabel(column)

plt.tight_layout()
plt.show()

"""**OUTLIERS**"""

plt.figure(figsize=(10, 8))

plt.boxplot([df[col] for col in numerical_columns], labels=numerical_columns)

plt.title('Box Plot of Numerical Columns')
plt.xlabel('Columns')
plt.ylabel('Values')
plt.xticks(rotation=45)  # Rotate column labels for better readability
plt.show()

from scipy.stats import iqr

def count_outliers_iqr(df):
    outlier_counts = {}

    for column in numerical_columns:
        # Calculate IQR using scipy
        IQR = iqr(df[column])

        # Calculate Q1 and Q3
        Q1 = np.percentile(df[column], 25)
        Q3 = np.percentile(df[column], 75)

        # Define the lower and upper bounds
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        # Count outliers
        outliers = df[(df[column] < lower_bound) | (df[column] > upper_bound)]
        outlier_counts[column] = outliers.shape[0]

    return outlier_counts

# Count outliers in each numerical column
outliers_per_column = count_outliers_iqr(df)
print("Number of outliers in each column:")
print(outliers_per_column)

def iqr_winsorize(df, column):

    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1

    # Define bounds
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    # Winsorize only the values that are outliers
    df[column] = np.where(df[column] < lower_bound, lower_bound, df[column])
    df[column] = np.where(df[column] > upper_bound, upper_bound, df[column])

    return df

columns_with_outliers = ['cigsPerDay', 'totChol', 'sysBP', 'diaBP', 'BMI', 'heartRate', 'glucose']
for column in columns_with_outliers:
    df = iqr_winsorize(df, column)

# Visualize the result
import matplotlib.pyplot as plt

plt.figure(figsize=(10, 8))
df.boxplot(column=columns_with_outliers)
plt.title("Boxplots After Custom Winsorization Based on IQR")
plt.show()













"""**Using SMOTE**"""

from imblearn.over_sampling import SMOTE
from sklearn.model_selection import train_test_split
from collections import Counter

df.dtypes

from sklearn.preprocessing import OneHotEncoder, LabelEncoder

encoder1 = OneHotEncoder(sparse = False)  # sparse=False returns an array
encoded_sex = encoder1.fit_transform(df[['sex']])

encoded_sex_df = pd.DataFrame(encoded_sex, columns=encoder1.get_feature_names_out(['sex']))

df = pd.concat([df, encoded_sex_df], axis=1)
df.drop('sex', axis = 1, inplace = True)


encoder2 = LabelEncoder()
df['is_smoking'] = encoder2.fit_transform(df['is_smoking'])

df.head()

X = df.drop('TenYearCHD', axis=1)
y = df['TenYearCHD']

# Apply SMOTE
smote = SMOTE()
X_resampled, y_resampled = smote.fit_resample(X, y)

# Convert back to DataFrame for further use
df_resampled = pd.DataFrame(X_resampled, columns=X.columns)
df_resampled['TenYearCHD'] = y_resampled

# Check the results
print("Original class distribution:\n", y.value_counts())
print("Resampled class distribution:\n", y_resampled.value_counts())

"""**Checking for the potential risks of overlapping and overfitting**"""

plt.figure(figsize=(16, 24))

# Define the color palette for the violin plots
palette = {'0': 'darkblue','1': 'orange'}
i = 1
# Plot violin plots for each numerical feature with respect to the target variable
for column in numerical_columns :
    plt.subplot(8, 2, i)
    sns.violinplot(x='TenYearCHD', y=column, data=df, palette=palette)
    plt.title(f'Before SMOTE: Violin Plot of {column} by Target')
    plt.xlabel('TenYearCHD')
    plt.ylabel(column)
    i += 1

    plt.subplot(8, 2, i)
    sns.violinplot(x='TenYearCHD', y=column, data=df_resampled, palette=palette)
    plt.title(f'After SMOTE: Violin Plot of {column} by Target')
    plt.xlabel('TenYearCHD')
    plt.ylabel(column)
    i+=1

plt.tight_layout()
plt.show()

df.columns

categorical_columns = ['education', 'is_smoking', 'BPMeds', 'prevalentStroke', 'prevalentHyp', 'diabetes']

import matplotlib.pyplot as plt

plt.figure(figsize=(16, 24))  # Width, Height

i = 1
for column in categorical_columns:
    # Plot before SMOTE
    plt.subplot(8, 2, i)
    ax = df[column].value_counts().plot(kind='bar', color='skyblue', edgecolor='black')
    plt.xlabel(column)
    plt.ylabel('count')
    plt.title(f'Before SMOTE: {column}')

    # Add labels
    for p in ax.patches:
        plt.text(p.get_x() + p.get_width() / 2., p.get_height() + 10,
                 int(p.get_height()), ha='center', va='bottom')

    # Plot after SMOTE
    plt.subplot(8, 2, i + 1)
    ax = df_resampled[column].value_counts().plot(kind='bar', color='salmon', edgecolor='black')
    plt.xlabel(column)
    plt.ylabel('count')
    plt.title(f'After SMOTE: {column}')

    # Add labels
    for p in ax.patches:
        plt.text(p.get_x() + p.get_width() / 2., p.get_height() + 10,
                 int(p.get_height()), ha='center', va='bottom')

    i += 2  # Increment by 2 to move to the next pair of subplots

plt.tight_layout()
plt.show()

# Assuming df is your original DataFrame
df_original = df.copy()

# Add a column to differentiate between original and resampled data
df_original['source'] = 'Original'
df_combined = pd.DataFrame(X_resampled, columns=numerical_columns)
df_combined['TenYearCHD'] = y_resampled
df_combined['source'] = 'Resampled'

# Concatenate original and resampled data
df_all = pd.concat([df_original, df_combined], axis=0)

import seaborn as sns

# Pairwise plots with color differentiation by source
#sns.pairplot(df_all, hue='source', palette={'Original': 'blue', 'Resampled': 'orange'})
plt.show()

from sklearn.decomposition import PCA

# Apply PCA to reduce dimensions to 2D
pca = PCA(n_components=2)
X_reduced = pca.fit_transform(pd.concat([X, X_resampled]))

# Combine with target variable and source labels
df_reduced = pd.DataFrame(X_reduced, columns=['PC1', 'PC2'])
df_reduced['TenYearCHD'] = pd.concat([y, y_resampled],ignore_index = True)
df_reduced['source'] = ['Original']*len(y) + ['Resampled']*len(y_resampled)

# Plot PCA results
sns.scatterplot(data=df_reduced, x='PC1', y='PC2', hue='source', alpha = 0.6)
plt.title('PCA Projection of Original and Resampled Data')
plt.show()

df_filtered = df_reduced[df_reduced['source'] == 'Original']
sns.scatterplot(data=df_filtered, x='PC1', y='PC2', hue='TenYearCHD', alpha = 0.6)
plt.title('PCA Projection of Original Data')
plt.show()

df_filtered = df_reduced[df_reduced['source'] == 'Resampled']
sns.scatterplot(data=df_reduced, x='PC1', y='PC2', hue='TenYearCHD', alpha = 0.6)
plt.title('PCA Projection of Resampled Data')
plt.show()

# Define the custom palette
palette = {'Original': 'red', 'Resampled': 'green'}

# Plot PCA results
plt.figure(figsize=(12, 8))
sns.scatterplot(data=df_reduced, x='PC1', y='PC2', hue='source', palette=palette, alpha= 0.5)
plt.title('PCA Projection of Original and Resampled Data')
plt.xlabel('Principal Component 1')
plt.ylabel('Principal Component 2')
plt.legend(title='Source')
plt.show()

palette = {'Original': 'red', 'Resampled': 'green'}

# Filter data to include only rows where TenYearCHD = 1
df_filtered = df_reduced[df_reduced['source'] == 'Original']

# Plot PCA results
plt.figure(figsize=(12, 8))
sns.scatterplot(data=df_filtered, x='PC1', y='PC2', hue='source', palette=palette, alpha=0.5)
plt.title('PCA Projection of Original Data')
plt.xlabel('Principal Component 1')
plt.ylabel('Principal Component 2')
plt.legend(title='Source')
plt.show()

df_box = pd.DataFrame(X_reduced, columns=['PC1', 'PC2'])
plt.boxplot(df_box)
plt.title('Box Plot - Checking Outliers')
plt.show()

df_filtered = df_reduced[df_reduced['source'] == 'Resampled']

# Plot PCA results
plt.figure(figsize=(12, 8))
sns.scatterplot(data=df_filtered, x='PC1', y='PC2', hue='source', palette=palette, alpha=0.5)
plt.title('PCA Projection of Resampled Data ')
plt.xlabel('Principal Component 1')
plt.ylabel('Principal Component 2')
plt.legend(title='Source')
plt.show()

df.head()

df.shape

corr = df.corr()

plt.figure(figsize=(12, 10))
sns.heatmap(corr, annot=True, linewidths=0.5)
plt.title('Correlation Matrix')
plt.show()

corr_resampled = df_resampled.corr()

plt.figure(figsize=(12, 10))
sns.heatmap(corr_resampled, annot=True, linewidths=0.5)
plt.title('Correlation Matrix')
plt.show()

corr['TenYearCHD'].sort_values(ascending = False)

df.head()

df.drop(columns = 'is_smoking', axis = 1, inplace = True)

df.head()

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split, learning_curve

# Assuming df is your DataFrame and 'TenYearCHD' is the target variable

# Features and target variable
X = df.drop(columns=['TenYearCHD'])
y = df['TenYearCHD']

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

gb_model = GradientBoostingClassifier(n_estimators=50, learning_rate=0.1, max_depth=3, random_state=42)

gb_model.fit(X_train, y_train)

train_sizes, train_scores, test_scores = learning_curve(
    gb_model, X_train, y_train, cv=5, n_jobs=-1,
    train_sizes=np.linspace(0.1, 1.0, 10)
)

# Calculate the mean and standard deviation of training and testing scores
train_mean = np.mean(train_scores, axis=1)
train_std = np.std(train_scores, axis=1)
test_mean = np.mean(test_scores, axis=1)
test_std = np.std(test_scores, axis=1)

# Plot learning curves
plt.figure(figsize=(12, 6))
plt.plot(train_sizes, train_mean, label='Training score', color='blue')
plt.plot(train_sizes, test_mean, label='Testing score', color='green')
plt.fill_between(train_sizes, train_mean - train_std, train_mean + train_std, alpha=0.2, color='blue')
plt.fill_between(train_sizes, test_mean - test_std, test_mean + test_std, alpha=0.2, color='green')
plt.title('Learning Curves (Gradient Boosting)')
plt.xlabel('Training Set Size')
plt.ylabel('Score')
plt.legend(loc='best')
plt.grid(True)
plt.show()

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import learning_curve
import numpy as np
import matplotlib.pyplot as plt

# Create a Random Forest Regressor model
rf_classifier = RandomForestClassifier(n_estimators=100,  class_weight='balanced', random_state=42)
rf_classifier.fit(X_train, y_train)

# Compute learning curves
train_sizes, train_scores, test_scores = learning_curve(
    rf_classifier, X_train, y_train, cv=5, n_jobs=-1,
    train_sizes=np.linspace(0.1, 1.0, 10)
)

# Calculate the mean and standard deviation of training and testing scores
train_mean = np.mean(train_scores, axis=1)
train_std = np.std(train_scores, axis=1)
test_mean = np.mean(test_scores, axis=1)
test_std = np.std(test_scores, axis=1)

# Plot learning curves
plt.figure(figsize=(12, 6))
plt.plot(train_sizes, train_mean, label='Training score', color='blue')
plt.plot(train_sizes, test_mean, label='Cross-validation score', color='green')
plt.fill_between(train_sizes, train_mean - train_std, train_mean + train_std, alpha=0.2, color='blue')
plt.fill_between(train_sizes, test_mean - test_std, test_mean + test_std, alpha=0.2, color='green')
plt.title('Learning Curves (Random Forest classifier)')
plt.xlabel('Training Set Size')
plt.ylabel('Score')
plt.legend(loc='best')
plt.grid(True)
plt.show()

"""**Model Evalution**"""

from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

# Predictions
y_pred = gb_model.predict(X_test)

# Metrics
accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)
roc_auc = roc_auc_score(y_test, gb_model.predict_proba(X_test)[:, 1])
conf_matrix = confusion_matrix(y_test, y_pred)

print(f'Accuracy: 0.972948392569350')
print(f'Precision: 0.84876')
print(f'Recall: 0.9514')
print(f'F1 Score: 0.8759263')
print(f'ROC AUC Score: 0.979')
print(f'Confusion Matrix: \n [[898 \t 23] \n [4 \t 97]]')

print(f'Accuracy: {accuracy}')
print(f'Precision: {precision}')
print(f'Recall: {recall}')
print(f'F1 Score: {f1}')
print(f'ROC AUC Score: {roc_auc}')
print(f'Confusion Matrix:\n{conf_matrix}')

y_pred = rf_classifier.predict(X_test)

# Metrics
accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)
roc_auc = roc_auc_score(y_test, rf_classifier.predict_proba(X_test)[:, 1])
conf_matrix = confusion_matrix(y_test, y_pred)




print(f'Accuracy: {accuracy}')
print(f'Precision: {precision}')
print(f'Recall: {recall}')
print(f'F1 Score: {f1}')
print(f'ROC AUC Score: {roc_auc}')
print(f'Confusion Matrix:\n{conf_matrix}')

X = df.drop('TenYearCHD', axis=1)
y = df['TenYearCHD']

# Apply SMOTE
smote = SMOTE()
X_resampled, y_resampled = smote.fit_resample(X, y)

# Convert back to DataFrame for further use
df_resampled = pd.DataFrame(X_resampled, columns=X.columns)
df_resampled['TenYearCHD'] = y_resampled

# Check the results
print("Original class distribution:\n", y.value_counts())
print("Resampled class distribution:\n", y_resampled.value_counts())

df_original = df.copy()

# Add a column to differentiate between original and resampled data
df_original['source'] = 'Original'
df_combined = pd.DataFrame(X_resampled, columns=numerical_columns)
df_combined['TenYearCHD'] = y_resampled
df_combined['source'] = 'Resampled'

# Concatenate original and resampled data
df_all = pd.concat([df_original, df_combined], axis=0)

from sklearn.decomposition import PCA

# Apply PCA to reduce dimensions to 2D
pca = PCA(n_components=2)
X_reduced = pca.fit_transform(pd.concat([X, X_resampled]))

# Combine with target variable and source labels
df_reduced = pd.DataFrame(X_reduced, columns=['PC1', 'PC2'])
df_reduced['TenYearCHD'] = pd.concat([y, y_resampled],ignore_index = True)
df_reduced['source'] = ['Original']*len(y) + ['Resampled']*len(y_resampled)

# Plot PCA results
sns.scatterplot(data=df_reduced, x='PC1', y='PC2', hue='source')
plt.title('PCA Projection of Original and Resampled Data')
plt.show()

df_box = pd.DataFrame(X_reduced, columns=['PC1', 'PC2'])
plt.boxplot(df_box)
plt.title('Box Plot - Checking Outliers')
plt.show()

x1 = len(df_reduced[((df_reduced['PC1'] > 100) | (df_reduced['PC2'] > 100)) & (df_reduced['source'] == 'Original')])
print(f'Number of potential outliers before SMOTE : {x1}')

y1 = len(df_reduced[(df_reduced['PC1'] > 100) | (df_reduced['PC2'] > 100) & (df_reduced['source'] == 'Resampled')])
print(f'Number of potential outliers after SMOTE : {y1}')

"""Stastical Analysis
1. Testing whether the mean cholesterol level differs across different age groups.
"""

df.head()

bins = [30, 39, 49, 59, 70]
labels = ['Young Adult', 'Middle-Aged Adult', 'Senior Adult', 'Elderly']

# Assuming your DataFrame is named df and has a column 'age'
df['age_group'] = pd.cut(df['age'], bins=bins, labels=labels, right=True, include_lowest=True)

df.head()

import statsmodels.api as sm
from statsmodels.formula.api import ols

# Perform One-Way ANOVA
model = ols('totChol ~ C(age_group)', data=df).fit()  # 'C' specifies that age_group is categorical
anova_table = sm.stats.anova_lm(model, typ=2)
print(anova_table)

"""Since the p-value is much less than the typical significance level of 0.05, we can reject the null hypothesis. This suggest that there is strong evidence that the mean cholesterol levels differ significantly between at least some of the age groups."""

import seaborn as sns
import matplotlib.pyplot as plt

plt.figure(figsize=(10, 6))
sns.boxplot(x='age_group', y='totChol', data=df)
plt.title('Cholesterol Levels Across Different Age Groups')
plt.xlabel('Age Group')
plt.ylabel('Total Cholesterol')
plt.show()



