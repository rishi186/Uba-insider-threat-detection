# UBA System Evaluation Report

**Generated**: 2026-04-28T21:43:58.989702

## Executive Summary

| Metric | Value |
|--------|-------|
| Threat Detected | ✅ Yes |
| Detection Delay | 3 days |
| Precision | 100.00% |
| Recall | 100.00% |
| F1 Score | 1.0000 |

## Insider Threat Detection

- **Target User**: U105
- **Expected Activity Start**: Day 25
- **First Detection**: Day 28
- **Max Risk Score**: 100.0/100
- **High-Risk Events Flagged**: 2

## Precision & Recall Analysis

| Metric | Count |
|--------|-------|
| True Positives | 2 |
| False Positives | 0 |
| False Negatives | 0 |
| True Negatives | 2918 |

**Alert Threshold**: 70

## False Positive Analysis

- **Normal Users**: 124
- **Users with False Alarms**: 0
- **Total FP Events**: 0
- **FP Rate**: 0.00%

## Top 5 Risky Users

| Rank | User | Risk Score |
|------|------|------------|
| 1 | U105 ⚠️ | 117.1 |
| 2 | U143 | 70.7 |
| 3 | U188 | 59.4 |
| 4 | U123 | 43.9 |
| 5 | U176 | 22.9 |

## Verdict

✅ **System Successfully Detected Insider Threat**
