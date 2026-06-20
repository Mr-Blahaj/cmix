#include "ahp-router.h"

#include <math.h>
#include <stdlib.h>

namespace {
const float kProbabilityEpsilon = 1.0e-6f;
}

AHPRouter::AHPRouter()
    : entropy_threshold_(0.75f),
      bias_(-0.013031155f),
      base_weight_(1.2365483f),
      byte_weight_(0.10821672f),
      word_weight_(0.17155925f),
      semantic_weight_(-0.056576105f),
      predictions_(0),
      byte_escalations_(0),
      word_escalations_(0),
      semantic_escalations_(0),
      trace_(NULL),
      last_bit_probability_(0.5f),
      last_byte_probability_(0.5f),
      last_word_probability_(0.5f),
      last_semantic_probability_(0.5f),
      trace_pending_(false) {
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

float AHPRouter::Route(float bit_probability, float byte_probability,
    float word_probability, float semantic_probability) {
  ++predictions_;
  last_bit_probability_ = bit_probability;
  last_byte_probability_ = byte_probability;
  last_word_probability_ = word_probability;
  last_semantic_probability_ = semantic_probability;
  trace_pending_ = true;
  float probability = bit_probability;

  if (BinaryEntropy(probability) > entropy_threshold_) {
    ++byte_escalations_;
    ++word_escalations_;
    ++semantic_escalations_;
    const float base_log_odds = LogOdds(bit_probability);
    const float routed_log_odds =
        bias_ +
        base_weight_ * base_log_odds +
        byte_weight_ * (LogOdds(byte_probability) - base_log_odds) +
        word_weight_ * (LogOdds(word_probability) - base_log_odds) +
        semantic_weight_ * (LogOdds(semantic_probability) - base_log_odds);
    probability = 1.0f / (1.0f + expf(-routed_log_odds));
  }
  return probability;
}

void AHPRouter::Perceive(int bit) {
  if (trace_ != NULL && trace_pending_) {
    fprintf(trace_, "%.9g,%.9g,%.9g,%.9g,%d\n",
        last_bit_probability_, last_byte_probability_,
        last_word_probability_, last_semantic_probability_, bit);
  }
  trace_pending_ = false;
}

void AHPRouter::PrintStats(FILE* stream) const {
  if (predictions_ == 0) return;
  const double scale = 100.0 / predictions_;
  fprintf(stream,
      "AHP routes: byte %.2f%%, word %.2f%%, semantic %.2f%% "
      "(%llu bit predictions)\n",
      byte_escalations_ * scale, word_escalations_ * scale,
      semantic_escalations_ * scale,
      static_cast<unsigned long long>(predictions_));
}
