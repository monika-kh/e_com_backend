from rest_framework.pagination import PageNumberPagination


class ProductReviewPagination(PageNumberPagination):
    """
    Simple page-number pagination for product reviews.

    Default: 5 reviews per page.
    """

    page_size = 5
    page_size_query_param = "page_size"
    max_page_size = 50

