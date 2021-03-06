from mtypes import (
    Typ, Instance, Callable, TypeVisitor, UnboundType, ErrorType, Any, Void,
    NoneTyp, TypeVar, Overloaded, TupleType
)


Typ expand_type(Typ typ, dict<int, Typ> map):
    """Expand any type variable references in a type with the actual values of
    type variables in an instance.
    """
    return typ.accept(ExpandTypeVisitor(map))


Typ expand_type_by_instance(Typ typ, Instance instance):
    """Expand type variables in type using type variable values in an
    instance."""
    if instance.args == []:
        return typ
    else:
        dict<int, Typ> variables = {}
        for i in range(len(instance.args)):
            variables[i + 1] = instance.args[i]
        typ = expand_type(typ, variables)
        if isinstance(typ, Callable):
            list<tuple<int, Typ>> bounds = []
            for j in range(len(instance.args)):
                bounds.append((j + 1, instance.args[j]))
            typ = update_callable_implicit_bounds((Callable)typ, bounds)
        else:
            pass
        return typ


class ExpandTypeVisitor(TypeVisitor<Typ>):
    dict<int, Typ> variables  # Lower bounds
    
    void __init__(self, dict<int, Typ> variables):
        self.variables = variables
    
    Typ visit_unbound_type(self, UnboundType t):
        return t
    
    Typ visit_error_type(self, ErrorType t):
        return t
    
    Typ visit_any(self, Any t):
        return t
    
    Typ visit_void(self, Void t):
        return t
    
    Typ visit_none_type(self, NoneTyp t):
        return t
    
    Typ visit_instance(self, Instance t):
        args = self.expand_types(t.args)
        return Instance(t.typ, args, t.line, t.repr)
    
    Typ visit_type_var(self, TypeVar t):
        repl = self.variables.get(t.id, t)
        if isinstance(repl, Instance):
            inst = (Instance)repl
            # Return copy of instance with type erasure flag on.
            return Instance(inst.typ, inst.args, inst.line, inst.repr, True)
        else:
            return repl
    
    Typ visit_callable(self, Callable t):
        return Callable(self.expand_types(t.arg_types),
                        t.arg_kinds,
                        t.arg_names,
                        t.ret_type.accept(self),
                        t.is_type_obj(),
                        t.name,
                        t.variables,
                        self.expand_bound_vars(t.bound_vars), t.line, t.repr)
    
    Typ visit_overloaded(self, Overloaded t):
        Callable[] items = []
        for item in t.items():
            items.append((Callable)item.accept(self))
        return Overloaded(items)
    
    Typ visit_tuple_type(self, TupleType t):
        return TupleType(self.expand_types(t.items), t.line, t.repr)
    
    Typ[] expand_types(self, Typ[] types):
        Typ[] a = []
        for t in types:
            a.append(t.accept(self))
        return a
    
    list<tuple<int, Typ>> expand_bound_vars(self, list<tuple<int, Typ>> types):
        list<tuple<int, Typ>> a = []
        for id, t in types:
            a.append((id, t.accept(self)))
        return a


Callable update_callable_implicit_bounds(Callable t,
                                         list<tuple<int, Typ>> arg_types):
    # FIX what if there are existing bounds?
    return Callable(t.arg_types,
                    t.arg_kinds,
                    t.arg_names,
                    t.ret_type,
                    t.is_type_obj(),
                    t.name,
                    t.variables,
                    arg_types, t.line, t.repr)


tuple<Typ[], Typ> expand_caller_var_args(Typ[] arg_types,
                                             int fixed_argc):
    """Expand the caller argument types in a varargs call. Fixedargc
    is the maximum number of fixed arguments that the target function
    accepts.
    
    Return (fixed argument types, type of the rest of the arguments). Return
    (nil, nil) if the last (vararg) argument had an invalid type. If the vararg
    argument was not an array (nor dynamic), the last item in the returned
    tuple is nil.
    """
    if isinstance(arg_types[-1], TupleType):
        return arg_types[:-1] + ((TupleType)arg_types[-1]).items, None
    else:
        Typ item_type
        if isinstance(arg_types[-1], Any):
            item_type = Any()
        elif isinstance(arg_types[-1], Instance) and (
                ((Instance)arg_types[-1]).typ.full_name() == 'builtins.list'):
            # List.
            item_type = ((Instance)arg_types[-1]).args[0]
        else:
            return None, None
        
        if len(arg_types) > fixed_argc:
            return arg_types[:-1], item_type
        else:
            return (arg_types[:-1] +
                    [item_type] * (fixed_argc - len(arg_types) + 1), item_type)
