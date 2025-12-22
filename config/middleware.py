# config/middleware.py
"""
Custom middleware for security and rate limiting.
"""
import logging
from django.http import JsonResponse
from django_ratelimit.exceptions import Ratelimited

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """
    Middleware to handle rate limit exceptions gracefully.
    Returns a proper 429 Too Many Requests response when rate limits are exceeded.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        """Handle Ratelimited exceptions with a proper 429 response."""
        if isinstance(exception, Ratelimited):
            logger.warning(
                f"Rate limit exceeded: path={request.path}, "
                f"IP={request.META.get('REMOTE_ADDR')}, "
                f"user={getattr(request, 'user', 'anonymous')}"
            )

            # Check if it's an AJAX/API request
            if request.headers.get('Accept') == 'application/json' or \
               request.content_type == 'application/json':
                return JsonResponse(
                    {
                        'error': 'rate_limit_exceeded',
                        'message': 'Too many requests. Please try again later.',
                    },
                    status=429
                )

            # For regular requests, return a simple 429 response
            from django.shortcuts import render
            response = render(request, 'errors/429.html', status=429)
            response['Retry-After'] = '60'  # Suggest retry after 60 seconds
            return response

        return None
