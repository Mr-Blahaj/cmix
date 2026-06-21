#ifndef AHP_ROUTER_H
#define AHP_ROUTER_H

#include <cstdint>
#include <stdio.h>

// Learns a synchronized residual correction over CMIX's final probability.
// Encoder and decoder see the same past bits, so no model parameters need to
// be stored in the archive.
class AHPRouter {
 public:
  AHPRouter();
  ~AHPRouter();

  float Route(float bit_probability, float byte_probability,
      float word_probability, float semantic_probability);
  void Perceive(int bit);
  void PrintStats(FILE* stream) const;

  static float BinaryEntropy(float probability);

 private:
  static float LogOdds(float probability);
  static float ClampProbability(float probability);
  static float ClampFeature(float value);

  static const int kNumFeatures = 5;
  float weights_[kNumFeatures];
  float features_[kNumFeatures];
  float routed_probability_;
  float learning_rate_;
  float weight_decay_;

  uint64_t predictions_;
  uint64_t adaptive_predictions_;
  FILE* trace_;
  float last_bit_probability_;
  float last_byte_probability_;
  float last_word_probability_;
  float last_semantic_probability_;
  bool trace_pending_;
};

#endif
