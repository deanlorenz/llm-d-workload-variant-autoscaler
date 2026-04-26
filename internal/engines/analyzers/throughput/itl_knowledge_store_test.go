package throughput

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("itlKnowledgeStore", func() {
	var store *itlKnowledgeStore

	BeforeEach(func() {
		store = newITLKnowledgeStore()
	})

	It("returns false for an unknown key", func() {
		_, ok := store.load("missing|key")
		Expect(ok).To(BeFalse())
	})

	It("stores and loads a model", func() {
		m := ITLModel{A: 0.073, B: 0.006}
		store.store("ns|model|v1", m)

		loaded, ok := store.load("ns|model|v1")
		Expect(ok).To(BeTrue())
		Expect(loaded.A).To(Equal(m.A))
		Expect(loaded.B).To(Equal(m.B))
	})

	It("overwrites the previous model on repeated store", func() {
		store.store("ns|model|v1", ITLModel{A: 0.05, B: 0.004})
		store.store("ns|model|v1", ITLModel{A: 0.09, B: 0.008})

		loaded, ok := store.load("ns|model|v1")
		Expect(ok).To(BeTrue())
		Expect(loaded.A).To(BeNumerically("~", 0.09, 1e-9))
	})

	It("stores models for distinct keys independently", func() {
		store.store("ns|model|v1", ITLModel{A: 0.05, B: 0.004})
		store.store("ns|model|v2", ITLModel{A: 0.09, B: 0.008})

		m1, ok1 := store.load("ns|model|v1")
		m2, ok2 := store.load("ns|model|v2")

		Expect(ok1).To(BeTrue())
		Expect(ok2).To(BeTrue())
		Expect(m1.A).To(BeNumerically("~", 0.05, 1e-9))
		Expect(m2.A).To(BeNumerically("~", 0.09, 1e-9))
	})
})
