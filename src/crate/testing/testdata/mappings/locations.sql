create table locations (
    name string primary key,
    date timestamp,
    datetime timestamp,
    kind string,
    position integer,
    description string,
    details array(object)
) replicas 0
