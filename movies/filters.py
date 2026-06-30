import django_filters
from .models import Movie, Genre, Language

class MovieFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    genres = django_filters.ModelMultipleChoiceFilter(queryset=Genre.objects.all(), field_name='genres__name', to_field_name='name')
    languages = django_filters.ModelMultipleChoiceFilter(queryset=Language.objects.all(), field_name='languages__name', to_field_name='name')
    
    class Meta:
        model = Movie
        fields = ['genres', 'languages', 'search']
