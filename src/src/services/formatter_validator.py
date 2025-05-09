import logging
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

class DataFormatterValidatorModule:
    """
    Formats and validates data according to presentation requirements (FR-PRES-001, FR-VALID-001).

    Ensures counts are whole numbers and revenues are in SAR format.
    Validation ensures correct application of these formats.
    """

    def format_and_validate_data(
        self,
        data: list[dict],
        count_columns: list[str],
        revenue_columns: list[str]
    ) -> list[dict]:
        """
        Formats numerical data in query results based on column types.

        Applies formatting rules for counts (whole numbers) and revenues (SAR currency).
        Validation is performed by attempting the format; failures are logged.

        Args:
            data: A list of dictionaries representing rows of data (e.g., from DB query).
            count_columns: A list of column names expected to contain counts.
            revenue_columns: A list of column names expected to contain revenue values.

        Returns:
            A new list of dictionaries with formatted data.
            Returns original value for a cell if formatting/validation fails for that cell.
        """
        if not isinstance(data, list):
             logger.error(f"Invalid data type provided to formatter: {type(data)}. Expected list.")
             return data # Return original data if not a list

        formatted_data = []
        for row in data:
            if not isinstance(row, dict):
                logger.warning(f"Skipping row of invalid type: {type(row)}. Expected dict.")
                formatted_data.append(row) # Keep original row if not a dict
                continue

            formatted_row = {}
            for col_name, value in row.items():
                if col_name in count_columns:
                    formatted_row[col_name] = self._format_count(value, col_name)
                elif col_name in revenue_columns:
                    formatted_row[col_name] = self._format_revenue(value, col_name)
                else:
                    # Keep other columns as they are
                    formatted_row[col_name] = value
            formatted_data.append(formatted_row)

        return formatted_data

    def _format_count(self, value, col_name: str):
        """Formats a value as a whole number count (FR-PRES-001a)."""
        if value is None:
            return None
        try:
            # Attempt to convert to float first to handle decimals, then round to int
            # Use round() for standard rounding behavior (e.g., 1.5 rounds to 2)
            count_value = round(float(value))
            return f"{count_value:,}" # Format with commas for readability
        except (ValueError, TypeError):
            logger.warning(
                f"Validation/Formatting failed for count column '{col_name}': "
                f"Value '{value}' (type: {type(value).__name__}) is not a valid number. "
                "Returning original value."
            )
            return value # Return original value on failure

    def _format_revenue(self, value, col_name: str):
        """Formats a value as SAR currency (FR-PRES-001b)."""
        if value is None:
            return None
        try:
            # Use Decimal for precision with currency. Convert via string to handle
            # potential float input without intermediate precision loss.
            revenue_value = Decimal(str(value))
            # Format to 2 decimal places with commas and SAR suffix
            return f"{revenue_value:,.2f} SAR"
        except (InvalidOperation, ValueError, TypeError):
            logger.warning(
                f"Validation/Formatting failed for revenue column '{col_name}': "
                f"Value '{value}' (type: {type(value).__name__}) is not a valid number. "
                "Returning original value."
            )
            return value # Return original value on failure