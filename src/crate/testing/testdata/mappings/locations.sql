create table locations (
    name string primary key,
    date timestamp,
    datetime timestamp,
    kind string,
    position integer,
    description string
) replicas 0
