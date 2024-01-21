from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Slate
from rest_framework import status
from opto.utils import format_slate


@api_view(['GET'])
def get_slates(request):
    try:
        slates = Slate.objects.filter(sport='NBA')
        formatted_slates = []
        for slate in slates:
            formatted_slates.append({'id': str(slate.id), 'name': format_slate(slate)})
        return Response(formatted_slates, status=status.HTTP_200_OK)
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
