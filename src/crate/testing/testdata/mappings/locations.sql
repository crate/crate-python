create table locations (
    name string primary key,
    date timestamp,
    datetime_tz timestamp with time zone,
    datetime_notz timestamp without time zone,
    nullable_datetime timestamp,
    nullable_date timestamp,
    kind string,
    flag boolean,
    position integer,
    description string,
    details array(object)
) with (number_of_replicas=0)
