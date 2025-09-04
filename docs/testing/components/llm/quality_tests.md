# LLM Quality Tests Specification

## Overview

This document specifies all quality tests for Large Language Models, organized by testing phase (development vs runtime) and categorized by the quality aspect being tested.

## Quality Test Categories

### 1. Response Coherence

**Purpose:** Ensure LLM outputs are logically consistent and well-structured

### 2. Instruction Following

**Purpose:** Validate the LLM's ability to accurately follow given instructions

### 3. Output Formatting

**Purpose:** Verify outputs conform to requested formats (JSON, lists, etc.)

### 4. Hallucination Detection

**Purpose:** Identify when the LLM generates false or unsupported information

### 5. Response Consistency

**Purpose:** Ensure similar inputs produce consistent outputs

### 6. Token Efficiency

**Purpose:** Measure how efficiently the LLM uses tokens

## Development-Time Quality Tests

### Test 1: Basic Instruction Following

**Category:** Instruction Following
**Purpose:** Verify the LLM can follow simple, explicit instructions
**Method:** Provide clear instructions and validate compliance
**Success Criteria:** 95% compliance rate
**Frequency:** Every deployment

```python
test_cases = [
    {
        "instruction": "List exactly 5 colors, one per line",
        "validation": lambda r: len(r.strip().split('\n')) == 5
    },
    {
        "instruction": "Write a haiku about technology",
        "validation": lambda r: validate_haiku_structure(r)
    },
    {
        "instruction": "Respond with only 'YES' or 'NO': Is water wet?",
        "validation": lambda r: r.strip() in ['YES', 'NO']
    }
]
```

### Test 2: Complex Instruction Following

**Category:** Instruction Following
**Purpose:** Test ability to follow multi-step or conditional instructions
**Method:** Provide complex instructions with multiple requirements
**Success Criteria:** 85% compliance rate
**Frequency:** Every deployment

```python
complex_tests = [
    {
        "instruction": """
        1. Start your response with 'ANALYSIS:'
        2. List 3 pros and 3 cons
        3. End with a recommendation
        4. Keep total response under 200 words
        """,
        "validation": validate_complex_structure
    }
]
```

### Test 3: JSON Output Compliance

**Category:** Output Formatting
**Purpose:** Ensure valid JSON generation when requested
**Method:** Request JSON with specific schema
**Success Criteria:** 100% valid JSON, 95% schema compliance
**Frequency:** Every deployment

```python
json_tests = [
    {
        "prompt": "Return a JSON object with user information",
        "schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "number"},
                "email": {"type": "string", "format": "email"}
            },
            "required": ["name", "age"]
        }
    }
]
```

### Test 4: Structured Output Formats

**Category:** Output Formatting
**Purpose:** Test various structured output formats
**Method:** Request different formats (CSV, Markdown, XML)
**Success Criteria:** 90% format compliance
**Frequency:** Every deployment

```python
format_tests = [
    {
        "format": "markdown_table",
        "prompt": "Create a markdown table with 3 columns and 3 rows",
        "validation": validate_markdown_table
    },
    {
        "format": "csv",
        "prompt": "Generate CSV data with headers",
        "validation": validate_csv_format
    }
]
```

### Test 5: Factual Accuracy

**Category:** Hallucination Detection
**Purpose:** Detect generation of false information
**Method:** Ask questions with known answers
**Success Criteria:** <5% hallucination rate
**Frequency:** Every deployment

```python
factual_tests = [
    {
        "question": "What is the capital of France?",
        "expected": ["Paris"],
        "type": "exact"
    },
    {
        "question": "List the primary colors",
        "expected": ["red", "blue", "yellow"],
        "type": "contains_all"
    }
]
```

### Test 6: Consistency Across Runs

**Category:** Response Consistency
**Purpose:** Ensure deterministic behavior when needed
**Method:** Run same prompt multiple times with temperature=0
**Success Criteria:** 95% consistency rate
**Frequency:** Every deployment

```python
consistency_test = {
    "prompt": "Define machine learning in one sentence",
    "runs": 5,
    "temperature": 0,
    "validation": lambda responses: similarity_score(responses) > 0.95
}
```

### Test 7: Context Window Utilization

**Category:** Token Efficiency
**Purpose:** Test handling of different context sizes
**Method:** Provide varying amounts of context
**Success Criteria:** Appropriate response scaling
**Frequency:** Weekly

```python
context_tests = [
    {
        "context_size": "minimal",  # <100 tokens
        "task": "Summarize this paragraph",
        "expected_response_size": "short"
    },
    {
        "context_size": "large",  # >2000 tokens
        "task": "Extract key points",
        "expected_response_size": "medium"
    }
]
```

### Test 8: Response Coherence

**Category:** Response Coherence
**Purpose:** Evaluate logical flow and structure
**Method:** Analyze response structure and transitions
**Success Criteria:** Coherence score > 0.85
**Frequency:** Every deployment

```python
coherence_metrics = {
    "logical_flow": check_logical_transitions,
    "topic_consistency": check_topic_drift,
    "conclusion_alignment": check_conclusion_relevance,
    "paragraph_structure": check_paragraph_coherence
}
```

## Runtime Quality Tests

### Monitor 1: Output Quality Scoring

**Category:** Response Coherence
**Metrics Collected:** Quality score per response
**Alerting Thresholds:** Score < 0.7 triggers review
**Response Actions:** Flag for human review, adjust parameters

```python
runtime_quality_monitor = {
    "sample_rate": 0.1,  # Check 10% of responses
    "metrics": [
        "coherence_score",
        "relevance_score",
        "completeness_score"
    ],
    "alert_threshold": 0.7
}
```

### Monitor 2: Format Compliance Tracking

**Category:** Output Formatting
**Metrics Collected:** Format error rate
**Alerting Thresholds:** Error rate > 5%
**Response Actions:** Log errors, notify development team

```python
format_monitor = {
    "track": ["json_errors", "schema_violations", "format_failures"],
    "aggregation_window": "5m",
    "alert_on": "error_rate > 0.05"
}
```

### Monitor 3: Instruction Adherence

**Category:** Instruction Following
**Metrics Collected:** Instruction compliance rate
**Alerting Thresholds:** Compliance < 90%
**Response Actions:** Review prompts, adjust system instructions

```python
instruction_monitor = {
    "checks": [
        "word_count_compliance",
        "format_compliance",
        "task_completion"
    ],
    "baseline": 0.90
}
```

### Monitor 4: Response Time Analysis

**Category:** Token Efficiency
**Metrics Collected:** Response time, tokens used
**Alerting Thresholds:** P95 > 2s, avg tokens > 500
**Response Actions:** Optimize prompts, adjust max_tokens

```python
performance_monitor = {
    "metrics": {
        "response_time_ms": ["p50", "p95", "p99"],
        "tokens_used": ["avg", "max"],
        "tokens_per_second": ["avg"]
    },
    "alerts": {
        "p95_response_time": "> 2000",
        "avg_tokens": "> 500"
    }
}
```

### Monitor 5: Drift Detection

**Category:** Response Consistency
**Metrics Collected:** Response pattern changes
**Alerting Thresholds:** Significant drift detected
**Response Actions:** Investigate model changes, retrain baselines

```python
drift_detector = {
    "baseline_window": "7d",
    "detection_methods": [
        "embedding_distance",
        "topic_distribution",
        "response_length_distribution"
    ],
    "sensitivity": 0.15
}
```

## Test Execution Framework

### Development Testing Pipeline

```python
class LLMQualityTester:
    def run_development_tests(self, llm_config):
        results = {}

        # Run each test category
        results["instruction_following"] = self.test_instruction_following()
        results["output_formatting"] = self.test_output_formatting()
        results["hallucination"] = self.test_hallucination_rate()
        results["consistency"] = self.test_consistency()
        results["coherence"] = self.test_coherence()

        # Calculate composite score
        results["composite_quality"] = self.calculate_quality_score(results)

        return results
```

### Runtime Monitoring Pipeline

```python
class LLMQualityMonitor:
    def monitor_response(self, prompt, response):
        metrics = {}

        # Real-time quality checks
        metrics["coherence"] = self.score_coherence(response)
        metrics["format_valid"] = self.check_format(response)
        metrics["instruction_followed"] = self.check_instruction_adherence(prompt, response)

        # Update aggregated metrics
        self.update_metrics(metrics)

        # Check thresholds
        if self.should_alert(metrics):
            self.send_alert(metrics)

        return metrics
```

## Quality Score Calculation

### Composite Quality Score Formula

```python
def calculate_quality_score(test_results):
    weights = {
        "instruction_following": 0.25,
        "output_formatting": 0.20,
        "coherence": 0.20,
        "consistency": 0.15,
        "hallucination_rate": 0.20  # Inverted - lower is better
    }

    score = 0
    for category, weight in weights.items():
        if category == "hallucination_rate":
            # Invert hallucination rate (lower is better)
            score += (1 - test_results[category]) * weight
        else:
            score += test_results[category] * weight

    return score
```

## Integration with Agent Testing

Quality scores are inherited by agents:

```python
inheritable_quality_metrics = {
    "instruction_following_accuracy": 0.95,
    "output_format_compliance": 0.92,
    "response_coherence": 0.94,
    "hallucination_rate": 0.08,
    "response_consistency": 0.91,
    "token_efficiency": 0.88
}
```

## Best Practices

### 1. Test Data Management

- Maintain versioned test datasets
- Include edge cases and adversarial examples
- Regularly update test cases based on production issues
- Balance test coverage with execution time

### 2. Baseline Management

- Establish baselines for each model version
- Track metric trends over time
- Use statistical significance testing for changes
- Document expected variations

### 3. Continuous Improvement

- Analyze failed tests to improve prompts
- Update test thresholds based on real-world performance
- Add new tests for emerging quality issues
- Share learnings across teams

## Related Documentation

- [Security Tests Specification](security_tests.md)
- [LLM Testing Overview](README.md)
- [Test Inheritance](../../architecture/test_inheritance.md)
