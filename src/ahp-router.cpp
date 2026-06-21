#include "ahp-router.h"

#include <math.h>
#include <stdlib.h>

namespace {
const float kProbabilityEpsilon = 1.0e-6f;
}

AHPRouter::AHPRouter()
    : routed_probability_(0.5f),
      learning_rate_(3.0e-5f),
      weight_decay_(1.0e-7f),
      predictions_(0),
      adaptive_predictions_(0),
      trace_(NULL),
      last_bit_probability_(0.5f),
      last_byte_probability_(0.5f),
      last_word_probability_(0.5f),
      last_semantic_probability_(0.5f),
      trace_pending_(false) {
  for (int i = 0; i < kNumFeatures; ++i) {
    weights_[i] = 0;
    features_[i] = 0;
  }
  const char* trace_path = getenv("CMIX_AHP_TRACE");
  if (trace_path != NULL && trace_path[0] != '\0') {
    trace_ = fopen(trace_path, "wb");
  }
}

AHPRouter::~AHPRouter() {
  if (trace_ != NULL) fclose(trace_);
}

float AHPRouter::ClampProbability(float probability) {
  if (probability < kProbabilityEpsilon) return kProbabilityEpsilon;
  if (probability > 1.0f - kProbabilityEpsilon) {
    return 1.0f - kProbabilityEpsilon;
  }
  return probability;
}

float AHPRouter::BinaryEntropy(float probability) {
  const float p = ClampProbability(probability);
  return -p * log2f(p) - (1.0f - p) * log2f(1.0f - p);
}

float AHPRouter::LogOdds(float probability) {
  const float p = ClampProbability(probability);
  return logf(p / (1.0f - p));
}

float AHPRouter::ClampFeature(float value) {
  if (value < -6.0f) return -6.0f;
  if (value > 6.0f) return 6.0f;
  return value;
}

float AHPRouter::Route(float bit_probability, float byte_probability,
    float word_probability, float semantic_probability) {
  ++predictions_;
  last_bit_probability_ = bit_probability;
  last_byte_probability_ = byte_probability;
  last_word_probability_ = word_probability;
  last_semantic_probability_ = semantic_probability;
  trace_pending_ = true;
  ++adaptive_predictions_;

  const float base_log_odds = LogOdds(bit_probability);
  features_[0] = 1.0f;
  features_[1] = ClampFeature(base_log_odds);
  features_[2] =
      ClampFeature(LogOdds(byte_probability) - base_log_odds);
  features_[3] =
      ClampFeature(LogOdds(word_probability) - base_log_odds);
  features_[4] =
      ClampFeature(LogOdds(semantic_probability) - base_log_odds);

  float correction = 0;
  for (int i = 0; i < kNumFeatures; ++i) {
    correction += weights_[i] * features_[i];
  }
  routed_probability_ =
      1.0f / (1.0f + expf(-(base_log_odds + correction)));
  return routed_probability_;
}

void AHPRouter::Perceive(int bit) {
  if (trace_ != NULL && trace_pending_) {
    fprintf(trace_, "%.9g,%.9g,%.9g,%.9g,%d\n",
        last_bit_probability_, last_byte_probability_,
        last_word_probability_, last_semantic_probability_, bit);
  }
  if (trace_pending_) {
    const float error = routed_probability_ - bit;
    for (int i = 0; i < kNumFeatures; ++i) {
      const float gradient =
          error * features_[i] + weight_decay_ * weights_[i];
      weights_[i] -= learning_rate_ * gradient;
      if (weights_[i] < -2.0f) weights_[i] = -2.0f;
      if (weights_[i] > 2.0f) weights_[i] = 2.0f;
    }
  }
  trace_pending_ = false;
}

void AHPRouter::PrintStats(FILE* stream) const {
  if (predictions_ == 0) return;
  const double scale = 100.0 / predictions_;
  fprintf(stream,
      "AHP online residual: %.2f%% adaptive (%llu bit predictions); "
      "weights %.6f %.6f %.6f %.6f %.6f\n",
      adaptive_predictions_ * scale,
      static_cast<unsigned long long>(predictions_),
      weights_[0], weights_[1], weights_[2], weights_[3], weights_[4]);
}
