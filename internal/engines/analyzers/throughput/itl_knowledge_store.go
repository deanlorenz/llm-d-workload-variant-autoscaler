package throughput

// itlKnowledgeStore persists the last tier-1 ITL model fitted for each variant.
// It is consulted only at tier-3 (zero active replicas) when the observation
// window cannot be updated and no current replica metrics are available.
//
// Thread-safety: all access is protected by the enclosing ThroughputAnalyzer.mu.
// No separate lock is required.
type itlKnowledgeStore struct {
	models map[string]ITLModel
}

func newITLKnowledgeStore() *itlKnowledgeStore {
	return &itlKnowledgeStore{models: make(map[string]ITLModel)}
}

// store saves model as the most recent validated ITL model for key.
// Called after a successful tier-1 OLS fit.
func (s *itlKnowledgeStore) store(key string, m ITLModel) {
	s.models[key] = m
}

// load retrieves the stored ITL model for key.
// Returns (zero ITLModel, false) if no tier-1 model has been stored yet.
func (s *itlKnowledgeStore) load(key string) (ITLModel, bool) {
	m, ok := s.models[key]
	return m, ok
}
