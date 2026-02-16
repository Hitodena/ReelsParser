import hashlib

from app.core import load


class RobokassaService:
    """
    Service for interacting with Robokassa payment gateway.

    Handles generation of payment links and verification of result callbacks.
    """

    def __init__(self) -> None:
        """Initialize service with configuration from environment."""
        config = load()
        self.login = config.environment.robokassa_login
        self.password1 = config.environment.robokassa_password1
        self.password2 = config.environment.robokassa_password2

    def generate_payment_link(
        self,
        invoice_id: str,
        amount: float,
        description: str,
    ) -> str:
        """
        Generate a Robokassa payment link.

        Args:
            invoice_id: Unique invoice identifier.
            amount: Payment amount in rubles (will be formatted to 2 decimal places).
            description: Payment description shown to user.

        Returns:
            Full URL to Robokassa payment page.

        Example:
            >>> service = RobokassaService()
            >>> url = service.generate_payment_link("INV_123", 990.00, "Base plan")
        """
        # Generate MD5 signature: MerchantLogin:OutSum:InvoiceID:Password1
        signature = hashlib.md5(
            f"{self.login}:{amount:.2f}:{invoice_id}:{self.password1}".encode()
        ).hexdigest()

        return (
            f"https://auth.robokassa.ru/Merchant/Index.aspx?"
            f"MerchantLogin={self.login}&"
            f"OutSum={amount:.2f}&"
            f"InvoiceID={invoice_id}&"
            f"Description={description}&"
            f"SignatureValue={signature}"
        )

    def verify_result(
        self,
        out_sum: str,
        inv_id: str,
        signature: str,
    ) -> bool:
        """
        Verify Robokassa ResultURL callback signature.

        Args:
            out_sum: Payment amount from callback.
            inv_id: Invoice ID from callback.
            signature: Signature value from callback.

        Returns:
            True if signature is valid, False otherwise.

        Note:
            Uses Password2 for result verification as per Robokassa documentation.
        """
        expected = hashlib.md5(
            f"{out_sum}:{inv_id}:{self.password2}".encode()
        ).hexdigest()
        return signature.lower() == expected.lower()
