# -*- coding: utf-8 -*-
from django.views import generic
from django.db.models import get_model
from django.shortcuts import get_object_or_404

from synergy.templates.regions.views import RegionViewMixin

from django.core.urlresolvers import reverse

from synergy.contrib.prospects.forms import prospectform_factory, build_query


from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
import signals


class ProspectMixin(object):
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ProspectMixin, self).dispatch(*args, **kwargs)

    def get_prospect_variant(self):
        return get_model('prospects', 'ProspectVariant').objects.get(name=self.kwargs.get('variant'))

    def get_prospect(self):
        return self.get_prospect_variant().prospect

    def get_results(self, *args, **kwargs):
        results = self.get_prospect_variant().filter(**build_query(kwargs))
        signals.prospect_results_created.send(sender=self.get_prospect_variant(), results=results, request=self.request)
        return results


class ListView(ProspectMixin, RegionViewMixin, generic.FormView):

    def get_representation(self):
        return self.get_prospect_variant().listrepresentation.representation

    def get_form_class(self):
        return prospectform_factory(self.get_prospect(), self.kwargs.get('variant'))

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super(ListView, self).get_form_kwargs(*args, **kwargs)
        kwargs['request'] = self.request
        kwargs['instance'] = self.get_prospect_variant()
        return kwargs

    def get_context_data(self, *args, **kwargs):
        ctx = super(ListView, self).get_context_data(*args, **kwargs)

        ctx['title'] = u"%s" % self.get_prospect().verbose_name
        ctx['prospect'] = self.get_prospect()
        ctx['variant'] = self.get_prospect_variant()

        repr_obj = self.get_representation()
        ctx[repr_obj._meta.object_name.lower()] = repr_obj

        ctx.update(self.get_representation().get_context_data(*args, **kwargs))

        results = []
        if kwargs['form'].is_valid():
            results = self.get_results(**dict(kwargs['form'].cleaned_data))
        ctx['results'] = results
        return ctx

    def form_valid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


class DetailView(ProspectMixin, RegionViewMixin, generic.DetailView):

    def get_prospect_variant(self):
        return get_model('prospects', 'ProspectVariant').objects.get(name=self.kwargs.get('variant'))
    
    def get_queryset(self):
        return self.get_results(**self.get_query_dict())

    def get_query_dict(self):
        return {}

    def get_context_data(self, *args, **kwargs):
        ctx = super(DetailView, self).get_context_data(*args, **kwargs)
        ctx['title'] = u"%s" % self.get_object()
        ctx.update(self.get_prospect_variant().objectdetail.get_context_data(*args, **kwargs))
        ctx_operator = self.get_prospect_variant().objectdetail.context_operator
        if ctx_operator:
            ctx_operator(self.request, self.get_object(), ctx, *args, **kwargs)
        return ctx

