import { ResponseContext, RequestContext, HttpFile, HttpInfo } from '../http/http';
import { Configuration} from '../configuration'

import { CreateEmbeddingRequest } from '../models/CreateEmbeddingRequest';
import { CreateEmbeddingRequestInput } from '../models/CreateEmbeddingRequestInput';
import { CreateEmbeddingRequestModel } from '../models/CreateEmbeddingRequestModel';
import { CreateEmbeddingResponse } from '../models/CreateEmbeddingResponse';
import { CreateEmbeddingResponseUsage } from '../models/CreateEmbeddingResponseUsage';
import { Embedding } from '../models/Embedding';

import { ObservableEmbeddingsApi } from "./ObservableAPI";
import { EmbeddingsApiRequestFactory, EmbeddingsApiResponseProcessor} from "../apis/EmbeddingsApi";

export interface EmbeddingsApiCreateEmbeddingRequest {
    /**
     * 
     * @type CreateEmbeddingRequest
     * @memberof EmbeddingsApicreateEmbedding
     */
    createEmbeddingRequest: CreateEmbeddingRequest
}

export class ObjectEmbeddingsApi {
    private api: ObservableEmbeddingsApi

    public constructor(configuration: Configuration, requestFactory?: EmbeddingsApiRequestFactory, responseProcessor?: EmbeddingsApiResponseProcessor) {
        this.api = new ObservableEmbeddingsApi(configuration, requestFactory, responseProcessor);
    }

    /**
     * Creates an embedding vector representing the input text.
     * @param param the request object
     */
    public createEmbeddingWithHttpInfo(param: EmbeddingsApiCreateEmbeddingRequest, options?: Configuration): Promise<HttpInfo<CreateEmbeddingResponse>> {
        return this.api.createEmbeddingWithHttpInfo(param.createEmbeddingRequest,  options).toPromise();
    }

    /**
     * Creates an embedding vector representing the input text.
     * @param param the request object
     */
    public createEmbedding(param: EmbeddingsApiCreateEmbeddingRequest, options?: Configuration): Promise<CreateEmbeddingResponse> {
        return this.api.createEmbedding(param.createEmbeddingRequest,  options).toPromise();
    }

}
