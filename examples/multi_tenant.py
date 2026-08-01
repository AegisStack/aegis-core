"""
Multi-tenant policy loading example.

Shows how to load customer-specific policies.
"""

import aegis


def process_payment(amount: float) -> dict:
    """Process a payment."""
    return {"payment_id": "pay_123", "amount": amount}


def main():
    # Register policy store (filesystem in this example)
    aegis.register_policy_store(
        backend="filesystem",
        base_path="./examples/policies",
        cache_ttl=60
    )

    # For different customers
    customers = ["acme-corp", "techco"]

    for customer in customers:
        print(f"\n=== Customer: {customer} ===")

        try:
            # Load customer-specific policy
            policy = aegis.load_customer_policy(customer)

            # Wrap tools with customer policy
            wrapped_tools = aegis.wrap(
                tools=[process_payment],
                policy=policy,
                agent_id="payment-agent",
                customer_id=customer,
                audit_sink=aegis.FileSink(path=f"./audit/{customer}.jsonl"),
            )

            # Test with different amounts
            for amount in [100, 500, 3000]:
                try:
                    result = wrapped_tools[0](amount=amount)
                    print(f"  Amount ${amount}: [OK] Allowed")
                except aegis.AegisViolationError:
                    print(f"  Amount ${amount}: [DENIED]")

        except aegis.AegisPolicyLoadError as e:
            print(f"  Policy not found for {customer}: {e}")


if __name__ == "__main__":
    main()
