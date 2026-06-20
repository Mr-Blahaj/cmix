#ifndef AHP_ROUTER_H
#define AHP_ROUTER_H

#include <cstdint>
#include <stdio.h>

// Routes the final coding probability through progressively richer experts
// while binary entropy remains high.
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

  float entropy_threshold_;
  float bias_;
  float base_weight_;
  float byte_weight_;
  float word_weight_;
  float semantic_weight_;

  uint64_t predictions_;
  uint64_t byte_escalations_;
  uint64_t word_escalations_;
  uint64_t semantic_escalations_;
  FILE* trace_;
  float last_bit_probability_;
  float last_byte_probability_;
  float last_word_probability_;
  float last_semantic_probability_;
  bool trace_pending_;
};

#endif
