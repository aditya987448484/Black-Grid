#!/usr/bin/env python3
"""Test script for forecast pipeline components"""

import sys
sys.path.insert(0, '/Users/adityapareek/BlackGrid/backend')

import numpy as np
import pandas as pd
from app.pipelines.features import FeaturePipeline
from app.models.baseline_model import BaselineModel

def test_feature_pipeline():
    """Test feature pipeline with mock data"""
    print("Testing Feature Pipeline...")
    
    fp = FeaturePipeline()
    
    # Create mock OHLCV data
    dates = pd.date_range('2024-01-01', periods=150)
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(150) * 2)
    
    df = pd.DataFrame({
        'Date': dates,
        'Open': prices + np.random.randn(150) * 0.5,
        'High': prices + np.abs(np.random.randn(150) * 0.5),
        'Low': prices - np.abs(np.random.randn(150) * 0.5),
        'Close': prices,
        'Volume': np.random.randint(1000000, 10000000, 150),
    })
    df.set_index('Date', inplace=True)
    
    features_df, feature_cols = fp.build_features(df)
    
    print(f"✅ Feature Pipeline Works:")
    print(f"   - Built {len(feature_cols)} features")
    print(f"   - Output shape: {features_df.shape}")
    print(f"   - Feature sample: {feature_cols[:3]}")
    
    return features_df, feature_cols, fp

def test_baseline_model(features_df, feature_cols, fp):
    """Test baseline model training and prediction"""
    print("\nTesting Baseline Model...")
    
    bm = BaselineModel()
    
    # Train on mock data
    metrics = bm.train(features_df, feature_cols, test_size=0.2)
    
    # Make prediction
    X_recent = fp.get_recent_features(features_df, feature_cols, lookback_days=60)
    X_latest = fp.flatten_features(X_recent)[-1]
    pred = bm.predict(X_latest)
    
    print(f"✅ Baseline Model Works:")
    print(f"   - Trained with {metrics['n_samples']} samples")
    print(f"   - Training accuracy: {metrics['accuracy']:.2%}")
    print(f"   - Prediction signal: {pred.signal}")
    print(f"   - Expected return: {pred.expected_return:.2f}%")
    print(f"   - Confidence: {pred.confidence:.1f}%")
    print(f"   - Explanation: {pred.explanation}")

if __name__ == "__main__":
    try:
        features_df, feature_cols, fp = test_feature_pipeline()
        test_baseline_model(features_df, feature_cols, fp)
        print("\n✅ All forecast pipeline components functional!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
