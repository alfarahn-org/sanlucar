import io

import openai
import pytest
import scripts
import tenacity
from conftest import MockAzureCredential
from scripts.prepdocs.files import (
    AzureOpenAIEmbeddingService,
    File,
    OpenAIEmbeddingService,
)


def test_filename_to_id():
    empty = io.BytesIO()
    empty.name = "foo.pdf"
    # test ascii filename
    assert File(empty).filename_to_id() == "file-foo_pdf-666F6F2E706466"
    # test filename containing unicode
    empty.name = "foo\u00A9.txt"
    assert File(empty).filename_to_id() == "file-foo__txt-666F6FC2A92E747874"
    # test filenaming starting with unicode
    empty.name = "ファイル名.pdf"
    assert File(empty).filename_to_id() == "file-______pdf-E38395E382A1E382A4E383ABE5908D2E706466"


@pytest.mark.asyncio
async def test_compute_embedding_success(monkeypatch):
    async def mock_create(*args, **kwargs):
        # From https://platform.openai.com/docs/api-reference/embeddings/create
        return {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "embedding": [
                        0.0023064255,
                        -0.009327292,
                        -0.0028842222,
                    ],
                    "index": 0,
                }
            ],
            "model": "text-embedding-ada-002",
            "usage": {"prompt_tokens": 8, "total_tokens": 8},
        }

    monkeypatch.setattr(openai.Embedding, "acreate", mock_create)
    embeddings = AzureOpenAIEmbeddingService(
        open_ai_service="x",
        open_ai_deployment="x",
        open_ai_model_name="text-ada-003",
        credential=MockAzureCredential(),
        disable_batch=False,
    )
    assert await embeddings.create_embeddings(texts=["foo"]) == [
        [
            0.0023064255,
            -0.009327292,
            -0.0028842222,
        ]
    ]

    embeddings = AzureOpenAIEmbeddingService(
        open_ai_service="x",
        open_ai_deployment="x",
        open_ai_model_name="text-ada-003",
        credential=MockAzureCredential(),
        disable_batch=True,
    )
    assert await embeddings.create_embeddings(texts=["foo"]) == [
        [
            0.0023064255,
            -0.009327292,
            -0.0028842222,
        ]
    ]

    embeddings = OpenAIEmbeddingService(
        open_ai_model_name="text-ada-003", credential=MockAzureCredential(), organization="org", disable_batch=False
    )
    assert await embeddings.create_embeddings(texts=["foo"]) == [
        [
            0.0023064255,
            -0.009327292,
            -0.0028842222,
        ]
    ]

    embeddings = OpenAIEmbeddingService(
        open_ai_model_name="text-ada-003", credential=MockAzureCredential(), organization="org", disable_batch=True
    )
    assert await embeddings.create_embeddings(texts=["foo"]) == [
        [
            0.0023064255,
            -0.009327292,
            -0.0028842222,
        ]
    ]


@pytest.mark.asyncio
async def test_compute_embedding_ratelimiterror_batch(monkeypatch, capsys):
    async def mock_acreate(*args, **kwargs):
        raise openai.error.RateLimitError

    monkeypatch.setattr(openai.Embedding, "acreate", mock_acreate)
    monkeypatch.setattr(tenacity.wait_random_exponential, "__call__", lambda x, y: 0)
    with pytest.raises(tenacity.RetryError):
        embeddings = AzureOpenAIEmbeddingService(
            open_ai_service="x",
            open_ai_deployment="x",
            open_ai_model_name="text-embedding-ada-002",
            credential=MockAzureCredential(),
            disable_batch=False,
            verbose=True,
        )
        await embeddings.create_embeddings(texts=["foo"])
    captured = capsys.readouterr()
    assert captured.out.count("Rate limited on the OpenAI embeddings API") == 14


@pytest.mark.asyncio
async def test_compute_embedding_ratelimiterror_single(monkeypatch, capsys):
    async def mock_acreate(*args, **kwargs):
        raise openai.error.RateLimitError

    monkeypatch.setattr(openai.Embedding, "acreate", mock_acreate)
    monkeypatch.setattr(tenacity.wait_random_exponential, "__call__", lambda x, y: 0)
    with pytest.raises(tenacity.RetryError):
        embeddings = AzureOpenAIEmbeddingService(
            open_ai_service="x",
            open_ai_deployment="x",
            open_ai_model_name="text-embedding-ada-002",
            credential=MockAzureCredential(),
            disable_batch=True,
            verbose=True,
        )
        await embeddings.create_embeddings(texts=["foo"])
    captured = capsys.readouterr()
    assert captured.out.count("Rate limited on the OpenAI embeddings API") == 14


def test_compute_embedding_autherror(monkeypatch, capsys):
    # monkeypatch.setattr(args, "verbose", True)

    def mock_create(*args, **kwargs):
        raise openai.error.AuthenticationError

    monkeypatch.setattr(openai.Embedding, "create", mock_create)
    monkeypatch.setattr(tenacity.nap.time, "sleep", lambda x: None)
    with pytest.raises(openai.error.AuthenticationError):
        # compute_embedding("foo", "ada", "text-ada-003")
        pass


def test_read_adls_gen2_files(monkeypatch, mock_data_lake_service_client):
    # monkeypatch.setattr(args, "verbose", True)
    # monkeypatch.setattr(args, "useacls", True)
    # monkeypatch.setattr(args, "datalakestorageaccount", "STORAGE")
    monkeypatch.setattr(scripts.prepdocs, "adls_gen2_creds", MockAzureCredential())

    def mock_remove(*args, **kwargs):
        pass

    class MockIndexSections:
        def __init__(self):
            self.filenames = []

        def call(self, filename, sections, acls):
            if filename == "a.txt":
                assert acls == {"oids": ["A-USER-ID"], "groups": ["A-GROUP-ID"]}
            elif filename == "b.txt":
                assert acls == {"oids": ["B-USER-ID"], "groups": ["B-GROUP-ID"]}
            elif filename == "c.txt":
                assert acls == {"oids": ["C-USER-ID"], "groups": ["C-GROUP-ID"]}
            else:
                raise Exception(f"Unexpected filename {filename}")

            self.filenames.append(filename)

    mock_index_sections = MockIndexSections()

    def mock_index_sections_method(filename, sections, acls):
        mock_index_sections.call(filename, sections, acls)

    monkeypatch.setattr(scripts.prepdocs, "remove_blobs", mock_remove)
    monkeypatch.setattr(scripts.prepdocs, "upload_blobs", mock_remove)
    monkeypatch.setattr(scripts.prepdocs, "remove_from_index", mock_remove)
    monkeypatch.setattr(scripts.prepdocs, "get_document_text", mock_remove)
    monkeypatch.setattr(scripts.prepdocs, "update_embeddings_in_batch", mock_remove)
    monkeypatch.setattr(scripts.prepdocs, "create_sections", mock_remove)
    monkeypatch.setattr(scripts.prepdocs, "index_sections", mock_index_sections_method)

    # read_adls_gen2_files(use_vectors=True, vectors_batch_support=True)

    assert mock_index_sections.filenames == ["a.txt", "b.txt", "c.txt"]
