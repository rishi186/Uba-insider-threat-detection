"""
Master Pipeline Runner - Executes the complete UBA & ITD pipeline.

Usage:
    python run_all.py                    # Run complete pipeline
    python run_all.py --skip-training    # Skip model training
    python run_all.py --only-evaluate    # Only run evaluation
"""

import argparse
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def print_header(text: str):
    """Print formatted header."""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")


def run_data_generation():
    """Step 1: Generate synthetic data."""
    print_header("STEP 1: DATA GENERATION")
    
    from data_pipeline.generator import generate_daily_logs
    from data_pipeline.mouse_generator import generate_edge_telemetry
    generate_daily_logs()
    generate_edge_telemetry()


def run_normalization():
    """Step 2: Normalize and unify data."""
    print_header("STEP 2: DATA NORMALIZATION")
    
    from data_pipeline.normalization import load_and_normalize
    load_and_normalize()


def run_feature_engineering():
    """Step 3: Calculate behavioral features."""
    print_header("STEP 3: FEATURE ENGINEERING")
    
    try:
        from data_pipeline.feature_engineering import run_feature_engineering
        from utils.config import config
        
        input_path = config.get_full_path('data_processed') + "/master_timeline.parquet"
        output_path = config.get_full_path('data_processed') + "/featured_timeline.parquet"
        
        run_feature_engineering(input_path, output_path)
    except Exception as e:
        print(f"Warning: Feature engineering failed: {e}")
        print("Continuing with basic features...")


def run_model_training():
    """Step 4: Train role-based LSTM models."""
    print_header("STEP 4: MODEL TRAINING (Role-Based LSTM)")
    
    try:
        from models.train_role_lstm import train_role_models
        train_role_models()
    except Exception as e:
        print(f"Warning: Role-based training failed: {e}")
        print("Falling back to basic LSTM training...")
        
        try:
            from models.train_lstm import train
            train()
        except Exception as e2:
            print(f"Error: Basic training also failed: {e2}")


def run_risk_pipeline():
    """Step 5: Run risk scoring pipeline."""
    print_header("STEP 5: RISK SCORING PIPELINE")
    
    try:
        from risk_engine.run_risk import run_risk_pipeline as _run_risk
        _run_risk()
    except Exception as e:
        print(f"Error: Risk pipeline failed: {e}")
        import traceback
        traceback.print_exc()


def run_evaluation():
    """Step 6: Evaluate system performance."""
    print_header("STEP 6: SYSTEM EVALUATION")
    
    try:
        from evaluation.evaluate_system import run_evaluation
        results = run_evaluation()
        return results
    except Exception as e:
        print(f"Warning: Evaluation failed: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="UBA & ITD Master Pipeline Runner")
    parser.add_argument("--skip-generation", action="store_true", help="Skip data generation")
    parser.add_argument("--skip-training", action="store_true", help="Skip model training")
    parser.add_argument("--only-evaluate", action="store_true", help="Only run evaluation")
    parser.add_argument("--only-risk", action="store_true", help="Only run risk pipeline")
    args = parser.parse_args()
    
    start_time = datetime.now()
    
    print("\n" + "#"*70)
    print("#" + " "*68 + "#")
    print("#" + "   UBA & INSIDER THREAT DETECTION - MASTER PIPELINE".center(68) + "#")
    print("#" + f"   Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}".center(68) + "#")
    print("#" + " "*68 + "#")
    print("#"*70 + "\n")
    
    if args.only_evaluate:
        run_evaluation()
    elif args.only_risk:
        run_risk_pipeline()
    else:
        # Full pipeline
        if not args.skip_generation:
            run_data_generation()
            run_normalization()
            run_feature_engineering()
        
        if not args.skip_training:
            run_model_training()
        
        run_risk_pipeline()
        run_evaluation()
    
    # Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print("\n" + "#"*70)
    print("#" + " "*68 + "#")
    print("#" + "   PIPELINE COMPLETE".center(68) + "#")
    print("#" + f"   Duration: {elapsed:.1f} seconds".center(68) + "#")
    print("#" + " "*68 + "#")
    print("#"*70 + "\n")
    
    print("Next steps:")
    print("  1. Start backend:  python -m uvicorn src.api.main_v2:app --port 8000")
    print("  2. Start frontend: cd website && npm run dev")
    print("  3. View reports:   data/risk_output/evaluation_report.md")


if __name__ == "__main__":
    main()
