from __future__ import unicode_literals, print_function
import inspect
import six
from django.db import models
from django.test import TestCase
from mock import MagicMock, patch
from random import randint
from url_filter.filterset import (FilterSetOptions,
                                  FilterSetMeta,
                                  BaseFilterSet,
                                  FilterSet)


class TestFilterSetOptions(TestCase):
    def test_has_attrs(self):
        opts = FilterSetOptions()
        attrs = ['model', 'fields', 'exclude']
        for attr in attrs:
            self.assertTrue(hasattr(opts, attr))

        expected = dict([(a, randint(1, 100)) for a in attrs])
        _opts = type(str('Options'), (object,), expected)
        opts = FilterSetOptions(_opts)
        for attr in attrs:
            self.assertEqual(getattr(opts, attr), expected.get(attr))


class TestFilterSetMeta(TestCase):
    def test_new(self):
        model = randint(1, 100)
        d1 = randint(1, 100)
        d2 = randint(1, 100)

        issub = MagicMock()
        issub.return_value = True
        declared_filters = MagicMock()
        declared_filters.return_value = {
            'foo': d1,
        }
        filters_model = MagicMock()
        filters_model.return_value = filters_model
        filters_model.update.return_value = {
            'foo': d1,
            'bar': d2,
        }

        opts = MagicMock()
        opts.model = randint
        opts.side_effect = lambda *a, **k: FilterSetOptions(*a, **k)

        with patch.multiple('url_filter.filterset',
                            get_declared_filters=declared_filters,
                            filters_for_model=filters_model,
                            FilterSetOptions=opts):
            meta = type(str('Meta'), (object,), {'model': model})
            fs = FilterSetMeta(str('FilterSet'), (object,), {'Meta': meta})
            declared_filters.assert_called_with((object,), {'Meta': meta})
            self.assertFalse(opts.called)
            self.assertFalse(hasattr(fs, 'base_filters'))

        with patch.multiple('url_filter.filterset',
                            get_declared_filters=declared_filters,
                            filters_for_model=filters_model,
                            FilterSetOptions=opts):
            if six.PY2:
                built = '__builtin__'
            else:
                built = 'builtins'
            with patch('{0}.issubclass'.format(built), issub):
                meta = type(str('Meta'), (object,), {})
                fs = FilterSetMeta(str('FilterSet'), (object,), {'Meta': meta})
                opts.assert_called_with(meta)
                self.assertFalse(filters_model.called)
                self.assertEqual(fs.base_filters, {'foo': d1})

                meta = type(str('Meta'), (object,), {'model': model})
                fs = FilterSetMeta(str('FilterSet'), (object,), {'Meta': meta})
                filters_model.assert_called_with(model, None, None)
                filters_model.update.assert_called_with({'foo': d1})
                self.assertEqual(fs.base_filters, filters_model)


class TestBaseFilterSet(TestCase):
    def test_init(self):
        qs = randint(1, 100)
        base_filters = randint(1, 100)
        opts = MagicMock()
        opts.model.objects.all.return_value = qs
        copy = MagicMock()
        copy.side_effect = lambda x: x

        # cannot be patched since they don't exist
        BaseFilterSet._meta = opts
        BaseFilterSet.base_filters = base_filters

        with patch('url_filter.filterset.deepcopy', copy):
            base = BaseFilterSet()
            opts.model.objects.all.assert_called_with()
            copy.assert_called_with(base_filters)
            self.assertEqual(base.data, {})
            self.assertEqual(base.queryset, qs)
            self.assertEqual(base.filters, base_filters)

            opts.reset_mock()

            base = BaseFilterSet(data='foo', queryset='bar')
            self.assertFalse(opts.model.object.all.called)
            self.assertEqual(base.data, 'foo')
            self.assertEqual(base.queryset, 'bar')

        # clean up
        del BaseFilterSet._meta
        del BaseFilterSet.base_filters

    def test_qs(self):
        copy = MagicMock()
        copy.side_effect = lambda x: x
        f1 = randint(1, 100)
        f2 = randint(1, 100)
        filter = MagicMock()
        filter.filter_dict.return_value = {
            'filter': {
                'foo': f1
            },
            'exclude': {
                'bar': f2
            }
        }
        base_filters = {
            'foo': filter,
        }
        d1 = randint(1, 100)
        data = {
            'bar': randint(1, 100),
            'foo': d1,
        }
        qs = MagicMock()
        qs.filter.side_effect = lambda **x: qs
        qs.exclude.side_effect = lambda **x: qs

        # manual patch
        BaseFilterSet.base_filters = base_filters

        # ----------------------------

        base = BaseFilterSet(data=None, queryset='foo')
        q = base.qs
        self.assertEqual(q, 'foo')
        self.assertFalse(filter.filter_dict.called)
        self.assertFalse(qs.filter.called)
        self.assertFalse(qs.exclude.called)

        # ----------------------------

        with patch('url_filter.filterset.deepcopy', copy):
            base = BaseFilterSet(data=data, queryset=qs)
            q = base.qs
            self.assertEqual(q, qs)
            filter.filter_dict.assert_called_with(qs, 'foo', d1)
            qs.filter.assert_called_with(foo=f1)
            qs.exclude.assert_called_with(bar=f2)

            filter.filter_dict.return_value = {
                'filter': {},
                'exclude': {},
            }

            base = BaseFilterSet(data=data, queryset=qs)
            q = base.qs
            self.assertEqual(q, qs)

        # cleanup
        del BaseFilterSet.base_filters


class TestFilterSet(TestCase):
    def test_class(self):
        self.assertTrue(issubclass(FilterSet, BaseFilterSet))
        # six's metaclass
        mro = [c.__name__ for c in inspect.getmro(FilterSet)]
        self.assertIn('NewBase', mro)

    def test_example(self):
        qs = MagicMock()
        qs.filter.return_value = qs

        class FooModel(models.Model):
            foo = models.CharField(max_length=16)

        class FS(FilterSet):
            class Meta(object):
                model = FooModel
                fields = ('id', 'foo')

        expected = {'id__exact': 1, 'foo__startswith': 'a'}
        FS(expected, qs).qs
        qs.filter.assert_called_with(**expected)
