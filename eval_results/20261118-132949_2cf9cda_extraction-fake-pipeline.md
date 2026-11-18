# Eval run `20261118-132949_2cf9cda_extraction-fake-pipeline`

- suites: extraction · split: **dev** · provider: fake
- git: `2cf9cda` · created 2026-11-18T13:29:49 · duration 0.21 s · cost $0.0000
- embedding model: BAAI/bge-small-en-v1.5 · models: {'extraction': 'claude-haiku-5-5'}
- prompt versions: extraction.v1
- config: `{"name": "default", "description": "", "index_name": null, "retrieval": {}, "qa": {}, "extraction": {}, "agent": {}}`
- note: fake provider: rule-based regex extractor - pipeline check only, NOT a model quality result
- note: extraction_real: labels are PROVISIONAL (verified_by_human=false); metrics on them are provisional

## extraction

```json
{
 "micro": {
  "precision": {
   "value": 0.9921414538310412,
   "k": 505,
   "n": 509,
   "ci": [
    0.98,
    0.9969
   ]
  },
  "recall": {
   "value": 0.9921414538310412,
   "k": 505,
   "n": 509,
   "ci": [
    0.98,
    0.9969
   ]
  },
  "f1": {
   "value": 0.9921414538310412,
   "n": 513
  }
 },
 "micro_f1": {
  "value": 0.9921414538310412,
  "n": 513
 },
 "per_field": {
  "part_number": {
   "precision": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "recall": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "f1": {
    "value": 1.0,
    "n": 33
   }
  },
  "manufacturer": {
   "precision": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "recall": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "f1": {
    "value": 1.0,
    "n": 33
   }
  },
  "product_name": {
   "precision": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "recall": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "f1": {
    "value": 1.0,
    "n": 33
   }
  },
  "category": {
   "precision": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "recall": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "f1": {
    "value": 1.0,
    "n": 33
   }
  },
  "supply_voltage_min_v": {
   "precision": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "recall": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "f1": {
    "value": 1.0,
    "n": 33
   }
  },
  "supply_voltage_max_v": {
   "precision": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "recall": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "f1": {
    "value": 1.0,
    "n": 33
   }
  },
  "rated_current_a": {
   "precision": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "recall": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "f1": {
    "value": 1.0,
    "n": 33
   }
  },
  "power_w": {
   "precision": {
    "value": 0.8846153846153846,
    "k": 23,
    "n": 26,
    "ci": [
     0.7102,
     0.96
    ]
   },
   "recall": {
    "value": 0.8846153846153846,
    "k": 23,
    "n": 26,
    "ci": [
     0.7102,
     0.96
    ]
   },
   "f1": {
    "value": 0.8846153846153846,
    "n": 29
   }
  },
  "operating_temp_min_c": {
   "precision": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "recall": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "f1": {
    "value": 1.0,
    "n": 33
   }
  },
  "operating_temp_max_c": {
   "precision": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "recall": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "f1": {
    "value": 1.0,
    "n": 33
   }
  },
  "ip_rating": {
   "precision": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "recall": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "f1": {
    "value": 1.0,
    "n": 33
   }
  },
  "weight_g": {
   "precision": {
    "value": 1.0,
    "k": 26,
    "n": 26,
    "ci": [
     0.8713,
     1.0
    ]
   },
   "recall": {
    "value": 1.0,
    "k": 26,
    "n": 26,
    "ci": [
     0.8713,
     1.0
    ]
   },
   "f1": {
    "value": 1.0,
    "n": 26
   }
  },
  "datasheet_revision": {
   "precision": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "recall": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "f1": {
    "value": 1.0,
    "n": 33
   }
  },
  "certifications": {
   "precision": {
    "value": 0.9696969696969697,
    "k": 32,
    "n": 33,
    "ci": [
     0.8468,
     0.9946
    ]
   },
   "recall": {
    "value": 0.9696969696969697,
    "k": 32,
    "n": 33,
    "ci": [
     0.8468,
     0.9946
    ]
   },
   "f1": {
    "value": 0.9696969696969697,
    "n": 34
   }
  },
  "interfaces": {
   "precision": {
    "value": 1.0,
    "k": 28,
    "n": 28,
    "ci": [
     0.8794,
     1.0
    ]
   },
   "recall": {
    "value": 1.0,
    "k": 28,
    "n": 28,
    "ci": [
     0.8794,
     1.0
    ]
   },
   "f1": {
    "value": 1.0,
    "n": 28
   }
  },
  "dimensions_mm": {
   "precision": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "recall": {
    "value": 1.0,
    "k": 33,
    "n": 33,
    "ci": [
     0.8957,
     1.0
    ]
   },
   "f1": {
    "value": 1.0,
    "n": 33
   }
  }
 },
 "evidence_validity": {
  "value": 1.0,
  "k": 509,
  "n": 509,
  "ci": [
   0.9925,
   1.0
  ]
 },
 "auto_validated_rate": {
  "value": 1.0,
  "k": 33,
  "n": 33,
  "ci": [
   0.8957,
   1.0
  ]
 },
 "needs_review_rate": {
  "value": 0.0,
  "k": 0,
  "n": 33,
  "ci": [
   0.0,
   0.1043
  ]
 },
 "validated_doc_precision": {
  "value": 0.8787878787878788,
  "k": 29,
  "n": 33,
  "ci": [
   0.7267,
   0.9518
  ]
 },
 "validated_field_precision": {
  "value": 0.9921414538310412,
  "k": 505,
  "n": 509,
  "ci": [
   0.98,
   0.9969
  ]
 },
 "attempts_mean": {
  "value": 1.0,
  "n": 33
 },
 "n_documents": 33
}
```

## extraction_real

```json
{
 "micro": {
  "precision": {
   "value": 0.3076923076923077,
   "k": 8,
   "n": 26,
   "ci": [
    0.165,
    0.4999
   ]
  },
  "recall": {
   "value": 0.11940298507462686,
   "k": 8,
   "n": 67,
   "ci": [
    0.0618,
    0.2183
   ]
  },
  "f1": {
   "value": 0.17204301075268816,
   "n": 85
  }
 },
 "micro_f1": {
  "value": 0.17204301075268816,
  "n": 85
 },
 "per_field": {
  "part_number": {
   "precision": {
    "value": null,
    "k": 0,
    "n": 0,
    "ci": [
     0.0,
     1.0
    ]
   },
   "recall": {
    "value": 0.0,
    "k": 0,
    "n": 6,
    "ci": [
     0.0,
     0.3903
    ]
   },
   "f1": {
    "value": 0.0,
    "n": 6
   }
  },
  "manufacturer": {
   "precision": {
    "value": null,
    "k": 0,
    "n": 0,
    "ci": [
     0.0,
     1.0
    ]
   },
   "recall": {
    "value": 0.0,
    "k": 0,
    "n": 6,
    "ci": [
     0.0,
     0.3903
    ]
   },
   "f1": {
    "value": 0.0,
    "n": 6
   }
  },
  "product_name": {
   "precision": {
    "value": null,
    "k": 0,
    "n": 0,
    "ci": [
     0.0,
     1.0
    ]
   },
   "recall": {
    "value": 0.0,
    "k": 0,
    "n": 6,
    "ci": [
     0.0,
     0.3903
    ]
   },
   "f1": {
    "value": 0.0,
    "n": 6
   }
  },
  "category": {
   "precision": {
    "value": null,
    "k": 0,
    "n": 0,
    "ci": [
     0.0,
     1.0
    ]
   },
   "recall": {
    "value": 0.0,
    "k": 0,
    "n": 6,
    "ci": [
     0.0,
     0.3903
    ]
   },
   "f1": {
    "value": 0.0,
    "n": 6
   }
  },
  "supply_voltage_min_v": {
   "precision": {
    "value": 0.5,
    "k": 1,
    "n": 2,
    "ci": [
     0.0945,
     0.9055
    ]
   },
   "recall": {
    "value": 0.2,
    "k": 1,
    "n": 5,
    "ci": [
     0.0362,
     0.6245
    ]
   },
   "f1": {
    "value": 0.28571428571428575,
    "n": 6
   }
  },
  "supply_voltage_max_v": {
   "precision": {
    "value": 0.5,
    "k": 1,
    "n": 2,
    "ci": [
     0.0945,
     0.9055
    ]
   },
   "recall": {
    "value": 0.2,
    "k": 1,
    "n": 5,
    "ci": [
     0.0362,
     0.6245
    ]
   },
   "f1": {
    "value": 0.28571428571428575,
    "n": 6
   }
  },
  "rated_current_a": {
   "precision": {
    "value": 0.3333333333333333,
    "k": 1,
    "n": 3,
    "ci": [
     0.0615,
     0.7923
    ]
   },
   "recall": {
    "value": 0.5,
    "k": 1,
    "n": 2,
    "ci": [
     0.0945,
     0.9055
    ]
   },
   "f1": {
    "value": 0.4,
    "n": 4
   }
  },
  "power_w": {
   "precision": {
    "value": 0.3333333333333333,
    "k": 1,
    "n": 3,
    "ci": [
     0.0615,
     0.7923
    ]
   },
   "recall": {
    "value": 0.5,
    "k": 1,
    "n": 2,
    "ci": [
     0.0945,
     0.9055
    ]
   },
   "f1": {
    "value": 0.4,
    "n": 4
   }
  },
  "operating_temp_min_c": {
   "precision": {
    "value": 0.5,
    "k": 1,
    "n": 2,
    "ci": [
     0.0945,
     0.9055
    ]
   },
   "recall": {
    "value": 0.2,
    "k": 1,
    "n": 5,
    "ci": [
     0.0362,
     0.6245
    ]
   },
   "f1": {
    "value": 0.28571428571428575,
    "n": 6
   }
  },
  "operating_temp_max_c": {
   "precision": {
    "value": 0.5,
    "k": 1,
    "n": 2,
    "ci": [
     0.0945,
     0.9055
    ]
   },
   "recall": {
    "value": 0.2,
    "k": 1,
    "n": 5,
    "ci": [
     0.0362,
     0.6245
    ]
   },
   "f1": {
    "value": 0.28571428571428575,
    "n": 6
   }
  },
  "ip_rating": {
   "precision": {
    "value": 0.16666666666666666,
    "k": 1,
    "n": 6,
    "ci": [
     0.0301,
     0.5635
    ]
   },
   "recall": {
    "value": 0.2,
    "k": 1,
    "n": 5,
    "ci": [
     0.0362,
     0.6245
    ]
   },
   "f1": {
    "value": 0.1818181818181818,
    "n": 10
   }
  },
  "weight_g": {
   "precision": {
    "value": null,
    "k": 0,
    "n": 0,
    "ci": [
     0.0,
     1.0
    ]
   },
   "recall": {
    "value": 0.0,
    "k": 0,
    "n": 4,
    "ci": [
     0.0,
     0.4899
    ]
   },
   "f1": {
    "value": 0.0,
    "n": 4
   }
  },
  "datasheet_revision": {
   "precision": {
    "value": null,
    "k": 0,
    "n": 0,
    "ci": [
     0.0,
     1.0
    ]
   },
   "recall": {
    "value": null,
    "k": 0,
    "n": 0,
    "ci": [
     0.0,
     1.0
    ]
   },
   "f1": {
    "value": 0.0,
    "n": 0
   }
  },
  "certifications": {
   "precision": {
    "value": 0.0,
    "k": 0,
    "n": 2,
    "ci": [
     0.0,
     0.6576
    ]
   },
   "recall": {
    "value": 0.0,
    "k": 0,
    "n": 2,
    "ci": [
     0.0,
     0.6576
    ]
   },
   "f1": {
    "value": 0.0,
    "n": 4
   }
  },
  "interfaces": {
   "precision": {
    "value": 0.0,
    "k": 0,
    "n": 3,
    "ci": [
     0.0,
     0.5615
    ]
   },
   "recall": {
    "value": 0.0,
    "k": 0,
    "n": 4,
    "ci": [
     0.0,
     0.4899
    ]
   },
   "f1": {
    "value": 0.0,
    "n": 7
   }
  },
  "dimensions_mm": {
   "precision": {
    "value": 1.0,
    "k": 1,
    "n": 1,
    "ci": [
     0.2065,
     1.0
    ]
   },
   "recall": {
    "value": 0.25,
    "k": 1,
    "n": 4,
    "ci": [
     0.0456,
     0.6994
    ]
   },
   "f1": {
    "value": 0.4,
    "n": 4
   }
  }
 },
 "evidence_validity": {
  "value": 0.8076923076923077,
  "k": 21,
  "n": 26,
  "ci": [
   0.6212,
   0.9149
  ]
 },
 "auto_validated_rate": {
  "value": 0.0,
  "k": 0,
  "n": 6,
  "ci": [
   0.0,
   0.3903
  ]
 },
 "needs_review_rate": {
  "value": 1.0,
  "k": 6,
  "n": 6,
  "ci": [
   0.6097,
   1.0
  ]
 },
 "validated_doc_precision": {
  "value": null,
  "k": 0,
  "n": 0,
  "ci": [
   0.0,
   1.0
  ]
 },
 "validated_field_precision": {
  "value": null,
  "k": 0,
  "n": 0,
  "ci": [
   0.0,
   1.0
  ]
 },
 "attempts_mean": {
  "value": 2.0,
  "n": 6
 },
 "n_documents": 6
}
```

## Ops

```json
{
 "extraction": {
  "latency_ms": {
   "n": 33,
   "p50": 1.0,
   "p95": 1.0,
   "mean": 1.0
  },
  "cost_usd": 0.0,
  "cost_per_document": 0.0,
  "llm_calls": 45,
  "input_tokens": 32185,
  "output_tokens": 15181
 }
}
```
