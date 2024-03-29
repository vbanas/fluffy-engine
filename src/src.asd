(asdf:defsystem :src
  :class :package-inferred-system
  :defsystem-depends-on (:asdf-package-system)
  :pathname #p"./"
  :depends-on (:src/main)
  :in-order-to ((asdf:test-op (asdf:load-op :src/test/test)))
  :perform (asdf:test-op
            (o c)
            (lisp-unit:run-tests :all :src/test/test)))

