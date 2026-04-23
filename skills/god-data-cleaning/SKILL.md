---
name: god-data-cleaning
description: "God-level data cleaning, preprocessing, and feature engineering skill. Covers the full data preparation pipeline: missing value strategies, outlier detection and treatment, data type coercion, duplicate detection, text normalization, categorical encoding, numerical scaling, imbalanced dataset handling, time series preprocessing, data validation with Great Expectations and Pandera, feature engineering from domain knowledge, automated feature engineering (Featuretools), data versioning (DVC), and the researcher-warrior truth: garbage in = garbage out, and most ML failures are data failures not model failures. Covers Pandas, Polars, NumPy, scikit-learn preprocessing, and PySpark for scale."
metadata:
  version: "1.0.0"
---

# God-Level Data Cleaning & Feature Engineering

## Researcher-Warrior Mindset

You are not a notebook jockey. You are a data warrior who understands that every assumption about a dataset is a potential bug in production. You verify everything. You trust nothing until you have inspected it. You know that the model is the last 20% of the work — the first 80% is data.

**Anti-hallucination mandate**: Never assert that a dataset is clean without running validation. Never assume an encoding, a date format, or a timezone. Never impute without understanding WHY data is missing. Always verify library API signatures against the installed version — sklearn, pandas, and polars all break APIs between major versions.

**Cross-domain mandate**: Apply lessons from bioinformatics (missing genotype data is MNAR), finance (zero volume means market closed, not zero volume), NLP (token frequency follows power law), and systems engineering (sensor dropout patterns encode system state) — data patterns from other domains often apply to your current problem.

---

## The Data Quality Manifesto

**80% of ML work is data work.** This is not a figure of speech — it is the measured reality from every serious ML deployment. A model trained on bad data learns to replicate the errors in that data with high confidence. A sophisticated model on corrupted data is more dangerous than a simple model on clean data, because it produces wrong answers with high confidence.

**Axioms every data practitioner must internalize:**

1. A model is only as good as its data. Period. No architecture choice compensates for systematic bias in labels.
2. Never skip exploratory data analysis (EDA). You will find things that invalidate your assumptions every single time.
3. Data leakage is the most common reason ML systems work in development and fail in production. It almost always originates in data preparation, not modeling.
4. Distribution shift is a data problem, not a model problem. Monitor your input distributions in production with the same rigor you monitor model outputs.
5. Reproducibility starts at the data level. A model trained on an undocumented dataset version is not reproducible.
6. Garbage in = garbage out. No exception. Ever.
7. Most ML "model failures" in production are actually data pipeline failures: schema drift, upstream system changes, silent data corruption.

**The cost of skipping data analysis:** In 2012, a major financial institution deployed a credit risk model that performed brilliantly in backtesting. It collapsed within 3 months of deployment. Root cause: a single boolean column had its encoding convention reversed by an upstream ETL change. No validation suite caught it because there was no validation suite. The model's AUC dropped from 0.82 to 0.51 — worse than random on the affected segment. This is not a horror story. This is Tuesday.

---

## Missing Data Taxonomy — Why the Type Determines the Strategy

Understanding WHY data is missing is not academic — it determines which imputation strategies are statistically valid.

### MCAR — Missing Completely At Random
The probability of being missing is the same for all observations. Missingness is independent of both the observed and unobserved data. Example: a random system error drops 2% of sensor readings with no pattern.

**Test**: Little's MCAR test (in `pyampute` or R's `mice` package). **Strategy**: Simple deletion is valid if the missing fraction is small (< 5%). Any imputation method is also valid since missingness is truly random.

### MAR — Missing At Random
The probability of being missing depends on observed data, but not on the unobserved values themselves. Example: women are less likely to report income (missingness depends on gender, which is observed), but given gender, missingness is random with respect to the income value itself.

**Test**: No definitive statistical test. Analyze missingness correlation with other features. **Strategy**: Multiple imputation (MICE) is the gold standard. Model-based imputation conditioned on correlated features is valid.

### MNAR — Missing Not At Random
The most dangerous type. The probability of being missing depends on the value itself. Example: people with very high or very low incomes are less likely to report income. Patients who are very sick are more likely to miss follow-up appointments. Sensors fail more often at extreme temperatures — the failure itself encodes information.

**Test**: No definitive test from data alone — requires domain knowledge. **Strategy**: You cannot impute MNAR data without making strong assumptions. Options: (1) model the missingness mechanism explicitly, (2) use pattern mixture models, (3) include a binary indicator for missingness as a feature (always do this for MNAR), (4) collect more data that explains the missingness. **Never** use mean/median imputation for MNAR — you are systematically biasing your analysis.

---

## Missing Value Strategies

### 1. Deletion

```python
# Listwise deletion — only valid for MCAR, small fraction
df.dropna(subset=['critical_column'])  # Drop rows with missing in specific column
df.dropna(thresh=df.shape[1] * 0.8)   # Keep rows with at least 80% non-null

# Column deletion — if a feature is >60% missing and MNAR, often the right call
missing_pct = df.isnull().mean()
df.drop(columns=missing_pct[missing_pct > 0.6].index, inplace=True)
```

**When**: MCAR, missing fraction < 5% for listwise. Column deletion when feature is mostly missing and unlikely to be imputable without introducing major bias.

### 2. Mean/Median/Mode Imputation

```python
from sklearn.impute import SimpleImputer
import pandas as pd

# Mean — only for normally distributed numeric, MCAR/MAR only
num_imputer = SimpleImputer(strategy='mean')
# Median — preferred for skewed distributions (more robust to outliers)
num_imputer = SimpleImputer(strategy='median')
# Most frequent — for categorical
cat_imputer = SimpleImputer(strategy='most_frequent')
# Constant — when domain knowledge specifies a fill value
const_imputer = SimpleImputer(strategy='constant', fill_value=0)
```

**When**: MCAR/MAR, numeric with roughly symmetric distribution (for mean), categorical (for mode). **Never for MNAR** — destroys the signal encoded in the missingness pattern.

### 3. KNN Imputation

```python
from sklearn.impute import KNNImputer

imputer = KNNImputer(n_neighbors=5, weights='uniform')
# weights='distance' gives closer neighbors more weight — usually better
df_imputed = pd.DataFrame(
    imputer.fit_transform(df[numeric_cols]),
    columns=numeric_cols
)
```

**When**: MAR, features have meaningful similarity structure, dataset is not too large (KNN is O(n) per query). KNN imputation respects local data structure. **Verify**: Fit on training data ONLY, transform train and test separately — this is a common source of data leakage.

### 4. Iterative Imputation (MICE Algorithm)

Multiple Imputation by Chained Equations — the gold standard for MAR data.

```python
from sklearn.experimental import enable_iterative_imputer  # Required import
from sklearn.impute import IterativeImputer
from sklearn.ensemble import RandomForestRegressor

# Default uses BayesianRidge — faster
imputer = IterativeImputer(max_iter=10, random_state=42)

# RandomForest estimator — more accurate, slower, handles non-linear relationships
imputer = IterativeImputer(
    estimator=RandomForestRegressor(n_estimators=10, random_state=42),
    max_iter=10,
    random_state=42
)

# Fit on training data ONLY
imputer.fit(X_train)
X_train_imputed = imputer.transform(X_train)
X_test_imputed = imputer.transform(X_test)
```

**Mechanism**: Iteratively regresses each feature with missing values on all other features. Cycles through all features until convergence. Handles multiple features simultaneously. **Warning**: `enable_iterative_imputer` is required as of scikit-learn 1.x — verify with your installed version.

### 5. Indicator Variable for Missingness

Always add a binary indicator when missingness is informative (MNAR, or MAR with high correlation to outcome).

```python
from sklearn.impute import MissingIndicator

indicator = MissingIndicator(features='missing-only')
missing_flags = indicator.fit_transform(df)
missing_flag_df = pd.DataFrame(
    missing_flags,
    columns=[f'{col}_was_missing' for col in df.columns[indicator.features_]]
)
df_augmented = pd.concat([df, missing_flag_df], axis=1)
```

---

## Outlier Detection

### IQR Method (Non-parametric, robust)
```python
Q1 = df['col'].quantile(0.25)
Q3 = df['col'].quantile(0.75)
IQR = Q3 - Q1
lower = Q1 - 1.5 * IQR
upper = Q3 + 1.5 * IQR
outliers = df[(df['col'] < lower) | (df['col'] > upper)]
```
**Use when**: No normality assumption, general-purpose. The 1.5x multiplier is Tukey's standard; use 3.0 for "extreme" outliers.

### Z-Score Method (Parametric)
```python
from scipy import stats
z_scores = np.abs(stats.zscore(df['col'].dropna()))
outliers = df[z_scores > 3]
```
**Use when**: Data is approximately normally distributed. Z > 3 captures ~0.3% of normal distribution.

### Modified Z-Score (Iglewicz-Hoaglin) — More Robust
```python
def modified_zscore(series):
    median = series.median()
    mad = (series - median).abs().median()  # Median Absolute Deviation
    return 0.6745 * (series - median) / mad  # 0.6745 = 1/Φ^-1(3/4)

scores = modified_zscore(df['col'])
outliers = df[scores.abs() > 3.5]  # 3.5 is the Iglewicz-Hoaglin threshold
```
**Use when**: Data may have heavy tails, MAD is more robust than standard deviation to outliers in the data being analyzed.

### Isolation Forest (Multivariate, model-based)
```python
from sklearn.ensemble import IsolationForest

iso = IsolationForest(contamination=0.05, random_state=42)
# contamination = expected fraction of outliers — requires domain knowledge
df['outlier_score'] = iso.fit_predict(df[numeric_features])
# Returns -1 for outliers, 1 for inliers
outliers = df[df['outlier_score'] == -1]
```
**Use when**: Multivariate outliers (not detectable in individual dimensions), high-dimensional data. Isolation Forest works by randomly partitioning data — outliers are easier to isolate (require fewer splits).

### Local Outlier Factor (Density-based)
```python
from sklearn.neighbors import LocalOutlierFactor

lof = LocalOutlierFactor(n_neighbors=20, contamination=0.05)
labels = lof.fit_predict(df[numeric_features])
# LOF does not support predict() after fit — must fit_predict together
outliers = df[labels == -1]
```
**Use when**: Clusters of different densities — LOF compares local density to neighbors' density. A point is an outlier if its density is significantly lower than its neighbors'.

### Outlier Treatment
```python
# 1. Winsorizing (capping) — replace extreme values with percentile boundaries
from scipy.stats.mstats import winsorize
df['col_winsorized'] = winsorize(df['col'], limits=[0.05, 0.05])

# 2. Log transform — compresses right tail, good for income/price/count data
df['col_log'] = np.log1p(df['col'])  # log1p handles zeros: log(1+x)

# 3. Separate model — flag outliers with an indicator, model separately
df['is_outlier'] = (iso.fit_predict(df[features]) == -1).astype(int)
```

---

## Duplicate Detection

### Exact Duplicates
```python
# Find exact duplicates
duplicates = df.duplicated(keep=False)  # Mark all duplicates
df_clean = df.drop_duplicates(keep='first')

# Duplicates on key columns only
duplicates = df.duplicated(subset=['customer_id', 'transaction_date'], keep=False)
```

### Near-Duplicate Detection with MinHash LSH
```python
from datasketch import MinHash, MinHashLSH

lsh = MinHashLSH(threshold=0.8, num_perm=128)
minhashes = {}
for idx, text in df['text_column'].items():
    m = MinHash(num_perm=128)
    for word in text.lower().split():
        m.update(word.encode('utf8'))
    lsh.insert(str(idx), m)
    minhashes[str(idx)] = m

# Find approximate duplicates
for idx, m in minhashes.items():
    result = lsh.query(m)
    if len(result) > 1:
        print(f"Near-duplicate group: {result}")
```

### Fuzzy String Matching with rapidfuzz
```python
from rapidfuzz import fuzz, process

# Single pair comparison
score = fuzz.ratio("John Smith", "Jon Smith")  # Token-based similarity

# Find best match from a list
match, score, index = process.extractOne("John Smith", name_list)

# Deduplicate a series
def deduplicate_fuzzy(series, threshold=85):
    seen = []
    canonical = {}
    for name in series:
        match = process.extractOne(name, seen, score_cutoff=threshold)
        if match:
            canonical[name] = match[0]
        else:
            seen.append(name)
            canonical[name] = name
    return series.map(canonical)
```

---

## Data Type Issues

```python
# Audit types immediately
print(df.dtypes)
print(df.select_dtypes(include='object').head())

# String numbers — convert with error handling
df['revenue'] = pd.to_numeric(df['revenue'], errors='coerce')
# errors='coerce' turns unconvertible values to NaN — always check what became NaN

# Mixed type columns — diagnose
for col in df.columns:
    types_in_col = df[col].dropna().apply(type).value_counts()
    if len(types_in_col) > 1:
        print(f"Mixed types in {col}: {types_in_col}")

# Date parsing — ALWAYS specify format, never rely on auto-detection
# Auto-detection is slow, inconsistent, and wrong for ambiguous dates like 01/02/03
df['date'] = pd.to_datetime(df['date_str'], format='%Y-%m-%d', utc=True)

# Timezone — always store UTC, convert on display
import pytz
df['timestamp_utc'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC')
df['timestamp_eastern'] = df['timestamp_utc'].dt.tz_convert('US/Eastern')

# Memory optimization — downcast numeric types
df['small_int'] = pd.to_numeric(df['small_int'], downcast='integer')
df['category_col'] = df['category_col'].astype('category')  # String -> category saves memory
```

---

## Categorical Encoding

### Label Encoding (Ordinal Only)
```python
from sklearn.preprocessing import OrdinalEncoder
enc = OrdinalEncoder(categories=[['low', 'medium', 'high']])
df['priority_encoded'] = enc.fit_transform(df[['priority']])
# NEVER use LabelEncoder for nominal categories — implies ordering that doesn't exist
```

### One-Hot Encoding
```python
# pandas — for nominal categories, low cardinality (<20 unique values)
df = pd.get_dummies(df, columns=['color', 'category'], drop_first=True)
# drop_first=True avoids multicollinearity (dummy variable trap)

# sklearn — integrates with Pipeline
from sklearn.preprocessing import OneHotEncoder
enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
# handle_unknown='ignore' is critical — new categories in production won't crash
```

### Target Encoding (Supervised, Leakage Risk)
```python
# Use cross-fold target encoding to prevent leakage
# category_encoders library provides this correctly
from category_encoders import TargetEncoder
from sklearn.model_selection import cross_val_predict

enc = TargetEncoder(cols=['high_cardinality_col'], smoothing=1.0)
# smoothing blends category mean with global mean for rare categories
# ALWAYS fit inside cross-validation folds — never fit on full training set then CV
```

### Hash Encoding (High Cardinality)
```python
from category_encoders import HashingEncoder
enc = HashingEncoder(cols=['user_id'], n_components=16)
# Dimensionality is fixed regardless of cardinality — no unknown category issue
# Accepts hash collisions as a tradeoff — acceptable when cardinality is very high
```

---

## Numerical Scaling

```python
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.preprocessing import PowerTransformer

# StandardScaler: zero mean, unit variance
# USE FOR: distance-based algorithms (KNN, SVM, PCA, logistic regression)
# NEVER FOR: tree-based models (they don't need it)
scaler = StandardScaler()

# MinMaxScaler: scales to [0, 1] range
# USE FOR: neural networks, algorithms requiring bounded input
# SENSITIVE TO: outliers — one extreme value compresses everything else
scaler = MinMaxScaler(feature_range=(0, 1))

# RobustScaler: uses median and IQR instead of mean and std
# USE FOR: data with outliers you don't want to remove
scaler = RobustScaler(quantile_range=(25.0, 75.0))

# Log transform for skewed distributions (right-skewed: income, page views, prices)
df['col_log'] = np.log1p(df['col'])  # log1p = log(1+x) handles zeros

# Box-Cox: requires strictly positive values, finds optimal lambda
from scipy.stats import boxcox
df['col_boxcox'], lambda_val = boxcox(df['col'] + 1)  # +1 to handle zeros

# Yeo-Johnson: like Box-Cox but handles zeros and negatives
pt = PowerTransformer(method='yeo-johnson')
df['col_yj'] = pt.fit_transform(df[['col']])

# ALWAYS: fit scaler on training data only, transform train and test separately
scaler.fit(X_train)
X_train_scaled = scaler.transform(X_train)
X_test_scaled = scaler.transform(X_test)  # Use training statistics
```

---

## Imbalanced Datasets

**Fundamental rule**: Never use accuracy for imbalanced datasets. A model that always predicts the majority class has 99% accuracy on a 1:99 dataset. Use PR-AUC, F1, MCC (Matthews Correlation Coefficient), or balanced accuracy.

```python
from imblearn.over_sampling import SMOTE, ADASYN
from imblearn.under_sampling import RandomUnderSampler
from imblearn.pipeline import Pipeline as ImbPipeline  # Not sklearn Pipeline

# SMOTE: Synthetic Minority Oversampling Technique
# Creates synthetic samples by interpolating between k nearest minority neighbors
smote = SMOTE(sampling_strategy='minority', k_neighbors=5, random_state=42)
X_resampled, y_resampled = smote.fit_resample(X_train, y_train)
# ONLY apply to training data — never to validation/test

# ADASYN: Adaptive Synthetic Sampling — focuses on hard examples near decision boundary
adasyn = ADASYN(sampling_strategy='minority', random_state=42)
X_resampled, y_resampled = adasyn.fit_resample(X_train, y_train)

# Class weights — often simpler and more effective than oversampling
from sklearn.utils.class_weight import compute_class_weight
weights = compute_class_weight('balanced', classes=np.unique(y), y=y)
class_weight_dict = dict(zip(np.unique(y), weights))
# Pass to model: RandomForestClassifier(class_weight='balanced')

# Threshold optimization — default 0.5 is often wrong for imbalanced data
from sklearn.metrics import precision_recall_curve
prec, rec, thresholds = precision_recall_curve(y_true, y_prob)
# Find threshold that maximizes F1
f1_scores = 2 * prec * rec / (prec + rec + 1e-8)
best_threshold = thresholds[np.argmax(f1_scores)]

# Correct evaluation metrics
from sklearn.metrics import matthews_corrcoef, average_precision_score
mcc = matthews_corrcoef(y_true, y_pred)           # MCC: -1 to +1, balanced
pr_auc = average_precision_score(y_true, y_prob)   # Area under PR curve
```

---

## Text Preprocessing

```python
import re
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer, WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer

def preprocess_text(text, language='english'):
    # 1. Lowercase
    text = text.lower()
    # 2. Remove URLs, HTML tags, special characters
    text = re.sub(r'http\S+|www\S+', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[^a-z0-9\s]', '', text)
    # 3. Tokenize
    tokens = word_tokenize(text)
    # 4. Remove stopwords (language-specific)
    stop = set(stopwords.words(language))
    tokens = [t for t in tokens if t not in stop and len(t) > 2]
    # 5. Lemmatize (better than stemming — produces real words)
    lemmatizer = WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(t) for t in tokens]
    return ' '.join(tokens)

# TF-IDF — for classical ML
tfidf = TfidfVectorizer(max_features=10000, ngram_range=(1, 2), min_df=2)
X_tfidf = tfidf.fit_transform(df['text'])

# Sentence Transformers — for semantic similarity, modern NLP
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(df['text'].tolist(), batch_size=32, show_progress_bar=True)
```

**Stemming vs Lemmatization**: PorterStemmer is fast but produces non-words ("running" → "run", "studies" → "studi"). WordNetLemmatizer produces real dictionary words and is more accurate but requires POS tagging for best results. Use lemmatization for production NLP pipelines.

---

## Time Series Preprocessing

```python
import pandas as pd
import numpy as np

# Always sort by time first — easy mistake to make, catastrophic if missed
df = df.sort_values('timestamp').reset_index(drop=True)

# Lag features — what happened N periods ago
for lag in [1, 7, 14, 30]:
    df[f'sales_lag_{lag}'] = df['sales'].shift(lag)

# Rolling statistics — context window features
df['sales_rolling_mean_7d'] = df['sales'].rolling(window=7).mean()
df['sales_rolling_std_7d'] = df['sales'].rolling(window=7).std()
df['sales_rolling_min_7d'] = df['sales'].rolling(window=7).min()
df['sales_rolling_max_7d'] = df['sales'].rolling(window=7).max()

# Differencing for stationarity
df['sales_diff1'] = df['sales'].diff(1)        # First difference
df['sales_diff7'] = df['sales'].diff(7)        # Seasonal difference (weekly)

# Stationarity test — ADF test
from statsmodels.tsa.stattools import adfuller
result = adfuller(df['sales'].dropna())
print(f'ADF Statistic: {result[0]:.4f}, p-value: {result[1]:.4f}')
# p < 0.05: reject null of unit root → stationary

# Handle irregular intervals — resample to regular grid
df = df.set_index('timestamp').resample('1H').agg({'value': 'mean'})
df['value'] = df['value'].interpolate(method='time')  # Fill gaps with time interpolation

# Time-based train/test split — NEVER random split for time series
split_date = '2024-01-01'
train = df[df.index < split_date]
test = df[df.index >= split_date]

# Datetime feature engineering
df['hour'] = df.index.hour
df['day_of_week'] = df.index.dayofweek   # 0=Monday, 6=Sunday
df['month'] = df.index.month
df['is_weekend'] = df.index.dayofweek.isin([5, 6]).astype(int)
df['days_since_launch'] = (df.index - df.index.min()).days
```

---

## Data Validation

### Great Expectations
```python
import great_expectations as gx

context = gx.get_context()

# Create expectation suite
suite = context.add_expectation_suite("my_dataset_suite")
validator = context.get_validator(...)  # Connect to your data source

# Define expectations
validator.expect_column_to_exist("customer_id")
validator.expect_column_values_to_not_be_null("customer_id")
validator.expect_column_values_to_be_unique("customer_id")
validator.expect_column_values_to_be_between("age", min_value=0, max_value=150)
validator.expect_column_values_to_be_in_set("status", ["active", "inactive", "pending"])
validator.expect_column_value_lengths_to_be_between("zip_code", min_value=5, max_value=10)
validator.expect_column_proportion_of_unique_values_to_be_between(
    "country", min_value=0.01, max_value=0.10
)
validator.save_expectation_suite()
```

### Pandera — Schema Validation in Code
```python
import pandera as pa
from pandera import Column, DataFrameSchema, Check

schema = DataFrameSchema({
    "customer_id": Column(str, Check(lambda s: s.str.match(r'^C\d{6}$')), nullable=False, unique=True),
    "age": Column(int, Check.in_range(0, 150), nullable=False),
    "revenue": Column(float, Check.greater_than_or_equal_to(0), nullable=True),
    "status": Column(str, Check.isin(["active", "inactive"]), nullable=False),
    "created_at": Column(pa.DateTime, nullable=False),
})

# Validate — raises SchemaError if invalid
validated_df = schema.validate(df)

# Use as decorator for functions
@pa.check_input(schema)
def process_customers(df: pd.DataFrame) -> pd.DataFrame:
    return df[df['status'] == 'active']
```

---

## Feature Engineering

### Domain-Knowledge Features
```python
# Interaction features — capture relationships between variables
df['revenue_per_employee'] = df['revenue'] / (df['employees'] + 1)
df['price_to_earnings'] = df['price'] / (df['earnings'] + 1e-8)

# Binning strategies
# Equal-width binning
df['age_bin'] = pd.cut(df['age'], bins=10, labels=False)
# Equal-frequency binning (quantile-based)
df['revenue_quartile'] = pd.qcut(df['revenue'], q=4, labels=['Q1','Q2','Q3','Q4'])
# Decision-tree-based binning — let the model find the boundaries
from sklearn.tree import DecisionTreeClassifier
tree = DecisionTreeClassifier(max_leaf_nodes=5).fit(df[['age']], df['churn'])
df['age_bin_tree'] = tree.apply(df[['age']])

# Datetime features
df['hour'] = pd.to_datetime(df['created_at']).dt.hour
df['day_of_week'] = pd.to_datetime(df['created_at']).dt.dayofweek
df['is_month_end'] = pd.to_datetime(df['created_at']).dt.is_month_end.astype(int)
df['days_since_last_purchase'] = (
    pd.Timestamp.now() - pd.to_datetime(df['last_purchase_date'])
).dt.days
```

---

## Polars vs Pandas vs PySpark

### Polars — When to Use
```python
import polars as pl

# Lazy evaluation — computations planned before execution, optimized automatically
df = (
    pl.scan_parquet("data/*.parquet")  # Lazy — nothing loaded yet
    .filter(pl.col("status") == "active")
    .with_columns([
        (pl.col("revenue") / pl.col("employees")).alias("rev_per_emp"),
        pl.col("created_at").str.to_date().dt.year().alias("year"),
    ])
    .group_by("year")
    .agg([pl.col("rev_per_emp").mean().alias("avg_rev_per_emp")])
    .collect()  # Execution happens here
)

# True parallelism — uses all CPU cores without GIL limitations
# 5-50x faster than Pandas for typical ETL operations
```

**Polars for**: Large datasets (>1GB), ETL pipelines, numerical operations, anything where speed matters.
**Pandas for**: Ecosystem compatibility (scikit-learn, seaborn, statsmodels), small datasets (<100MB), interactive exploration.

### PySpark — When to Scale
Move to PySpark when data doesn't fit in memory (typically >50GB for ETL, or when Polars is still too slow):

```python
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.ml.feature import VectorAssembler, StandardScaler

spark = SparkSession.builder.appName("DataCleaning").getOrCreate()
df = spark.read.parquet("s3://bucket/data/")

# Transformations are lazy — only executed on action (show, count, write)
df_clean = (df
    .filter(F.col("status") == "active")
    .withColumn("rev_per_emp", F.col("revenue") / (F.col("employees") + 1))
    .dropDuplicates(["customer_id"])
    .na.fill({"revenue": 0, "category": "unknown"})
)

df_clean.write.parquet("s3://bucket/clean/", mode="overwrite")
```

---

## Data Versioning with DVC

```bash
# Initialize DVC in a Git repo
dvc init
git add .dvc .dvcignore
git commit -m "Initialize DVC"

# Track a dataset
dvc add data/raw/customers.csv
git add data/raw/customers.csv.dvc data/raw/.gitignore
git commit -m "Track raw customers dataset"

# Remote storage (S3, GCS, Azure Blob, local)
dvc remote add -d myremote s3://my-bucket/dvc-store
dvc push  # Upload data to remote

# DVC pipeline stages
dvc stage add -n clean_data \
  -d data/raw/customers.csv \
  -d src/clean.py \
  -o data/processed/customers_clean.parquet \
  "python src/clean.py"

dvc repro  # Run pipeline, skip unchanged stages
dvc dag    # View pipeline DAG
```

DVC stores a `.dvc` file (hash of the data) in Git, and the actual data in remote storage. This gives you: reproducibility (hash = exact data version), collaboration (everyone pulls the same data), and pipeline caching (unchanged stages are skipped).

---

## Self-Review Checklist

Before any modeling step, verify every item below. If you cannot verify it, fix it first.

1. **Data audit complete**: shape, dtypes, missing values, unique counts, descriptive statistics for all columns.
2. **Missing data classified**: Is each missing column MCAR, MAR, or MNAR? Document the reasoning.
3. **No data leakage**: Target variable not used in imputation or encoding fitting on full dataset; all transformations fit on training data only.
4. **No temporal leakage**: For time series, train/test split is time-based, rolling statistics only use past values.
5. **Duplicates checked**: Exact and near-duplicate detection run, decision documented.
6. **Data types verified**: No string numbers, no mixed types, dates parsed with explicit format.
7. **Timezone standardized**: All timestamps stored in UTC.
8. **Distribution analyzed**: Histograms and box plots for all numeric features. Identified skewed distributions.
9. **Outliers investigated**: Not just detected — the cause of outliers is understood (data error vs real phenomenon).
10. **Categorical cardinality checked**: High-cardinality columns identified, encoding strategy chosen accordingly.
11. **Scaling appropriate**: Scaling applied where needed (distance-based algorithms), not applied blindly to tree models.
12. **Class imbalance handled**: For classification, imbalance ratio checked. Appropriate strategy applied.
13. **Validation suite defined**: At minimum a Pandera schema or Great Expectations suite that will catch upstream schema drift.
14. **Feature leakage audit**: Each engineered feature inspected to confirm it would be available at prediction time in production.
15. **Train/val/test splits documented**: Split rationale, sizes, and strategy are written down.
16. **Text preprocessing reproducible**: Exact preprocessing steps documented and implemented as a reusable function.
17. **Target distribution understood**: Label distribution for classification, target statistics for regression.
18. **Correlation analysis done**: High-correlation feature pairs identified — consider dropping redundant features.
19. **Data version tracked**: DVC or equivalent — the exact dataset hash used for training is recorded.
20. **Pipeline serialized**: Preprocessing pipeline saved (scikit-learn Pipeline + joblib) so production uses identical transformations with no reconstruction from memory.
