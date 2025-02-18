CREATE TABLE repositories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE commits (
    id INTEGER PRIMARY KEY,
    hash TEXT NOT NULL,
    author TEXT NOT NULL,
    commit_date DATETIME NOT NULL,
    message TEXT NOT NULL,
    repository_id INTEGER,
    FOREIGN KEY (repository_id) REFERENCES repositories(id)
);

CREATE TABLE files (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL,
    repository_id INTEGER,
    FOREIGN KEY (repository_id) REFERENCES repositories(id)
);

CREATE TABLE commit_files (
    commit_id INTEGER,
    file_id INTEGER,
    FOREIGN KEY (commit_id) REFERENCES commits(id),
    FOREIGN KEY (file_id) REFERENCES files(id),
    PRIMARY KEY (commit_id, file_id)
);

INSERT INTO repositories (name) VALUES
    ('ChangeCommerce.Products.API'),
    ('ChangeCommerce.ShopifyAppExt'),
    ('ChangeCommerce.Stores.API'),
    ('ChangeCommerce.Utilities.JS'),
    ('shoppinggives.widget-sdk');
