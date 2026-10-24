class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        location = '(self)' if request.path.startswith('/checkout/') else '()'
        response['Permissions-Policy'] = f'camera=(), microphone=(), geolocation={location}'
        # Django admin uses inline styles/scripts. Storefront scripts are local.
        response['Content-Security-Policy'] = (
            "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; font-src 'self'; connect-src 'self'; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        )
        if request.path.startswith(('/accounts/', '/account/', '/orders/', '/checkout/', '/bag/', '/wishlist/', '/admin/', '/internal/', '/webhooks/')):
            response['Cache-Control'] = 'private, no-store'
        return response
